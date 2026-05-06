"""Configuration for the PAC Intel Digest pipeline."""

import os
from pathlib import Path

# ==============================================================================
# GMAIL SETTINGS
# ==============================================================================

# Gmail OAuth2 credentials file (generated during setup)
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json")

# Gmail account email address (the dedicated monitoring inbox)
GMAIL_ACCOUNT = "your-monitoring-gmail@gmail.com"  # Update this

# Inbox label to read from (usually "INBOX")
GMAIL_INBOX_LABEL = "INBOX"

# How many hours back to look for unread emails
GMAIL_LOOKBACK_HOURS = 24

# ==============================================================================
# CLAUDE API SETTINGS
# ==============================================================================

# API key (will be injected via environment variable in GitHub Actions)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Model for email categorization and analysis
CLAUDE_MODEL_HAIKU = "claude-haiku-4-5-20251001"

# Model for digest content generation
CLAUDE_MODEL_SONNET = "claude-sonnet-4-6"

# ==============================================================================
# GITHUB SETTINGS
# ==============================================================================

# Repository owner and name
GITHUB_REPO_OWNER = "alittleagency"
GITHUB_REPO_NAME = "vncs-email-digest"

# GitHub token for pushing commits (injected via GitHub Actions)
GITHUB_TOKEN = os.getenv("GH_PAT")

# Branch to push to
GITHUB_BRANCH = "main"

# Output file path in the repo
OUTPUT_FILE = "index.html"

# GitHub Pages URL
GITHUB_PAGES_URL = f"https://{GITHUB_REPO_OWNER}.github.io/{GITHUB_REPO_NAME}"

# ==============================================================================
# EMAIL SETTINGS
# ==============================================================================

# Gmail SMTP server (Gmail's server)
EMAIL_SMTP_HOST = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# From address (the dedicated Gmail account sending the email)
EMAIL_FROM = GMAIL_ACCOUNT

# Recipient email address
EMAIL_TO = "email-tech@vncs.io"

# Email subject template (will be formatted with date)
EMAIL_SUBJECT_TEMPLATE = "PAC Intel Digest — {date_formatted}"

# ==============================================================================
# SENDER LOOKUP
# ==============================================================================

# Path to senders.json lookup table
SENDERS_JSON_FILE = "senders.json"

# ==============================================================================
# EMAIL CONTENT SETTINGS
# ==============================================================================

# Maximum characters of email body to extract
MAX_EMAIL_BODY_LENGTH = 500

# Default category for unrecognized senders
DEFAULT_CATEGORY = "flag"

# ==============================================================================
# PATHS
# ==============================================================================

# Root directory for the project
PROJECT_ROOT = Path(__file__).parent.absolute()

# Local clone directory for the GitHub repo
REPO_LOCAL_PATH = PROJECT_ROOT / "vncs-email-digest-local"
