#!/usr/bin/env python3
"""
VNCS Email Digest Pipeline

Reads Gmail inbox, analyzes emails with Claude API, generates HTML digest,
and deploys to GitHub Pages.
"""

import logging
import json
import base64
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from anthropic import Anthropic
from bs4 import BeautifulSoup
from git import Repo

import config
from claude_prompt import build_digest_prompt


# ==============================================================================
# LOGGING SETUP
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==============================================================================
# GMAIL AUTHENTICATION
# ==============================================================================

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth2 (installed app flow).
    Creates credentials.json if it doesn't exist.
    """
    creds = None

    if Path(config.GMAIL_CREDENTIALS_FILE).exists():
        creds = Credentials.from_authorized_user_file(
            config.GMAIL_CREDENTIALS_FILE, SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(config.GMAIL_CREDENTIALS_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ==============================================================================
# EMAIL FETCHING
# ==============================================================================

def fetch_unread_emails(gmail_service) -> List[Dict]:
    """
    Fetch all unread emails from the last 24 hours.

    Returns:
        List of dicts with: sender, subject, body, received_time
    """
    lookback_time = datetime.utcnow() - timedelta(hours=config.GMAIL_LOOKBACK_HOURS)
    query = f"is:unread after:{lookback_time.strftime('%Y/%m/%d')}"

    results = gmail_service.users().messages().list(
        userId="me", q=query, maxResults=100
    ).execute()

    messages = results.get("messages", [])
    logger.info(f"Found {len(messages)} unread emails in the last {config.GMAIL_LOOKBACK_HOURS} hours")

    emails = []
    for msg in messages:
        email_data = parse_email(gmail_service, msg["id"])
        if email_data:
            emails.append(email_data)

    return emails


def parse_email(gmail_service, message_id: str) -> Optional[Dict]:
    """Extract sender, subject, body, and timestamp from a Gmail message."""
    msg = gmail_service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers = msg["payload"].get("headers", [])
    header_dict = {h["name"]: h["value"] for h in headers}

    sender = header_dict.get("From", "Unknown")
    subject = header_dict.get("Subject", "(no subject)")
    date_str = header_dict.get("Date", "")

    body_text = extract_body_text(msg["payload"])
    body_preview = body_text[:config.MAX_EMAIL_BODY_LENGTH]

    return {
        "sender": sender,
        "subject": subject,
        "body": body_preview,
        "received_time": date_str,
        "full_body": body_text,
    }


def extract_body_text(payload: Dict) -> str:
    """Extract plain text body from email payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""


# ==============================================================================
# SENDER CATEGORIZATION
# ==============================================================================

def load_senders_lookup() -> Dict:
    """Load senders.json lookup table."""
    with open(config.SENDERS_JSON_FILE, "r") as f:
        return json.load(f)


def extract_organization_name(from_field: str) -> str:
    """
    Extract organization name from email From field.
    Handles: "Organization Name <email@domain.com>" or just "email@domain.com"
    """
    # Try to extract text before angle bracket
    match = re.match(r'^(.+?)\s*<', from_field)
    if match:
        org_name = match.group(1).strip()
        if org_name:
            return org_name

    # If no angle bracket, try to extract from email local part
    match = re.match(r'^([^@]+)', from_field)
    if match:
        return match.group(1).strip()

    return from_field.strip()


def categorize_senders(emails: List[Dict]) -> tuple[List[Dict], List[str]]:
    """
    Categorize each email by sender, mark new senders.

    Returns:
        (emails with category added, list of new sender org names)
    """
    senders_lookup = load_senders_lookup()
    all_senders = []
    for category in senders_lookup.values():
        all_senders.extend(category)

    new_senders = set()
    categorized_emails = []

    for email in emails:
        org_name = extract_organization_name(email["sender"])
        email["organization"] = org_name

        # Find category
        category = config.DEFAULT_CATEGORY
        for cat, orgs in senders_lookup.items():
            if org_name in orgs:
                category = cat
                break

        if category == config.DEFAULT_CATEGORY and org_name not in all_senders:
            new_senders.add(org_name)

        email["category"] = category
        categorized_emails.append(email)

    return categorized_emails, sorted(list(new_senders))


# ==============================================================================
# CLAUDE API DIGEST GENERATION
# ==============================================================================

def generate_digest_content(emails: List[Dict], new_senders: List[str]) -> Dict:
    """
    Call Claude Sonnet to generate digest content from emails.

    Returns:
        Parsed JSON response with trend_cards, spend_cards, flag_cards, stats
    """
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    prompt = build_digest_prompt(emails, new_senders)

    logger.info(f"Calling Claude Sonnet with {len(emails)} emails")

    response = client.messages.create(
        model=config.CLAUDE_MODEL_SONNET,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = response.content[0].text

    try:
        digest_data = json.loads(response_text)
        logger.info("Successfully generated digest content")
        return digest_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response text: {response_text}")
        raise


# ==============================================================================
# HTML TEMPLATE INJECTION
# ==============================================================================

def load_html_template() -> str:
    """
    Load HTML template from the repo.
    If this is the first run, fetch from GitHub Pages prototype.
    """
    template_path = Path("index.html")

    if template_path.exists():
        with open(template_path, "r") as f:
            return f.read()

    logger.info("No local template found, fetching from GitHub Pages prototype")
    import urllib.request
    try:
        with urllib.request.urlopen("https://alittleagency.github.io/intel_digest/") as response:
            return response.read().decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to fetch prototype template: {e}")
        raise


def inject_digest_content(html: str, digest_data: Dict, emails: List[Dict]) -> str:
    """
    Inject generated content into HTML template using BeautifulSoup.
    Modifies: trend cards, spend cards, flag cards, stats, datestamp, email list.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Update datestamp
    now = datetime.now()
    date_formatted = now.strftime("%A, %B %d, %Y at %I:%M %p")
    datestamp = soup.find(class_="datestamp")
    if datestamp:
        datestamp.string = date_formatted

    # Inject trend cards
    trends_container = soup.find("div", class_="trends-container")
    if trends_container:
        trends_container.clear()
        for trend in digest_data.get("trend_cards", []):
            card_html = f"""
            <div class="trend-card">
                <h3>{trend.get('topic', '')}</h3>
                <p class="angle">{trend.get('angle', '')}</p>
                <p class="senders">From: {', '.join(trend.get('senders', []))}</p>
                <div class="examples">
                    <strong>Examples:</strong>
                    <ul>
                        {''.join([f'<li>{subj}</li>' for subj in trend.get('example_subjects', [])])}
                    </ul>
                </div>
                <p class="heat">Heat: {trend.get('heat_score', 0)}/5</p>
            </div>
            """
            trends_container.append(BeautifulSoup(card_html, "html.parser"))

    # Inject spend cards
    spend_container = soup.find("div", class_="spend-container")
    if spend_container:
        spend_container.clear()
        for spend in digest_data.get("spend_cards", []):
            card_html = f"""
            <div class="spend-card">
                <h3>{spend.get('title', '')}</h3>
                <p>{spend.get('detail', '')}</p>
            </div>
            """
            spend_container.append(BeautifulSoup(card_html, "html.parser"))

    # Inject flag cards
    flag_container = soup.find("div", class_="flag-container")
    if flag_container:
        flag_container.clear()
        for flag in digest_data.get("flag_cards", []):
            severity = flag.get('severity', 'green').lower()
            card_html = f"""
            <div class="flag-card flag-{severity}">
                <span class="severity">{severity.upper()}</span>
                <h3>{flag.get('title', '')}</h3>
                <p>{flag.get('description', '')}</p>
            </div>
            """
            flag_container.append(BeautifulSoup(card_html, "html.parser"))

    # Update stats
    stats = digest_data.get("stats", {})
    stat_labels = {
        "emails": stats.get("total_emails", 0),
        "trends": stats.get("trending_topics_count", 0),
        "spend": stats.get("spend_signals_count", 0),
        "senders": stats.get("new_senders_count", 0),
    }

    for key, value in stat_labels.items():
        stat_el = soup.find(class_=f"stat-{key}")
        if stat_el:
            stat_el.string = str(value)

    # Inject email list
    email_table = soup.find("tbody", id="emailListBody")
    if email_table:
        email_table.clear()
        for email in emails:
            row_html = f"""
            <tr>
                <td>{email.get('organization', 'Unknown')}</td>
                <td>{email.get('subject', '(no subject)')}</td>
                <td>{email.get('received_time', '')}</td>
                <td><span class="badge badge-{email.get('category', 'flag')}">{email.get('category', 'flag').upper()}</span></td>
            </tr>
            """
            email_table.append(BeautifulSoup(row_html, "html.parser"))

    return str(soup)


# ==============================================================================
# GITHUB DEPLOYMENT
# ==============================================================================

def deploy_to_github(html_content: str) -> str:
    """
    Clone the GitHub repo, write index.html, commit, and push.

    Returns:
        GitHub Pages URL
    """
    repo_path = config.REPO_LOCAL_PATH

    # Clean up old clone if it exists
    if repo_path.exists():
        shutil.rmtree(repo_path)

    # Clone repo
    repo_url = f"https://x-access-token:{config.GITHUB_TOKEN}@github.com/{config.GITHUB_REPO_OWNER}/{config.GITHUB_REPO_NAME}.git"
    logger.info(f"Cloning repo to {repo_path}")
    repo = Repo.clone_from(repo_url, repo_path)

    # Write HTML
    output_file = repo_path / config.OUTPUT_FILE
    with open(output_file, "w") as f:
        f.write(html_content)

    # Commit and push
    repo.index.add(config.OUTPUT_FILE)
    now = datetime.now()
    commit_message = f"Update digest — {now.strftime('%Y-%m-%d %H:%M:%S')}"
    repo.index.commit(commit_message)
    repo.remotes.origin.push()

    logger.info(f"Pushed to {config.GITHUB_REPO_NAME}")

    return config.GITHUB_PAGES_URL



# ==============================================================================
# MAIN ORCHESTRATION
# ==============================================================================

def main():
    """Main pipeline orchestration."""
    try:
        logger.info("Starting VNCS Email Digest pipeline")

        # Step 1: Authenticate and fetch emails
        logger.info("Authenticating with Gmail")
        gmail_service = authenticate_gmail()

        logger.info("Fetching unread emails")
        emails = fetch_unread_emails(gmail_service)

        if not emails:
            logger.warning("No emails found, exiting")
            return

        # Step 2: Categorize senders
        logger.info("Categorizing senders")
        emails, new_senders = categorize_senders(emails)

        # Step 3: Generate digest content
        logger.info("Generating digest content with Claude")
        digest_data = generate_digest_content(emails, new_senders)

        # Step 4: Load template and inject content
        logger.info("Loading HTML template")
        html = load_html_template()

        logger.info("Injecting content into template")
        html_with_content = inject_digest_content(html, digest_data, emails)

        # Step 5: Deploy to GitHub
        logger.info("Deploying to GitHub Pages")
        pages_url = deploy_to_github(html_with_content)


        logger.info("Pipeline completed successfully")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
