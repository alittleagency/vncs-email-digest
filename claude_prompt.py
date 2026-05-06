"""Claude API prompt templates for VNCS Email Digest Digest."""

from typing import List, Dict


def build_digest_prompt(emails: List[Dict], new_senders: List[str]) -> str:
    """
    Build the prompt for Claude Sonnet to generate digest content.

    Args:
        emails: List of email dicts with keys: sender, subject, body, received_time
        new_senders: List of sender organization names not in senders.json

    Returns:
        Prompt string ready to send to Claude API
    """

    # Format email list for the prompt
    email_summary = "\n".join([
        f"- From: {email['sender']}\n  Subject: {email['subject']}\n  Preview: {email['body']}\n  Time: {email['received_time']}"
        for email in emails
    ])

    # Format new senders list
    new_senders_text = "\n".join([f"- {sender}" for sender in new_senders]) if new_senders else "None"

    prompt = f"""You are analyzing a daily digest of political intelligence emails from PACs, candidates, and political newsletters.

EMAILS RECEIVED IN THE LAST 24 HOURS:

{email_summary}

NEW/UNRECOGNIZED SENDERS TODAY:
{new_senders_text}

YOUR TASK:
Analyze these emails to identify genuine messaging trends, R-side spending signals, and flags worth alerting on.

REQUIREMENTS:
1. MESSAGING TRENDS (3-4 cards max): Identify coordinated language shifts, new framing, or volume spikes that indicate a real trend — not just "many emails today." Use actual subject lines as examples. Focus on D-side organizing.

2. GOP SPEND INTEL (3-4 cards max): From R-side emails, extract geographic spend signals, messaging frames, or budget priorities that D-side campaigns could use as urgency fodder. Be specific — include district names, dollar amounts if mentioned, and actual messaging frames.

3. FLAGS (3-5 cards max): New/unrecognized senders, volume spikes from known PACs, new PAC registrations mentioned in emails, race rating changes, industry news, or anything that warrants immediate attention.

4. SUMMARY STATS: Accurate counts of total emails, number of distinct trending topics identified, number of spend signals identified, and number of new senders.

RESPONSE FORMAT:
Return ONLY valid JSON (no markdown, no code blocks, no preamble) with this exact structure:

{{
  "trend_cards": [
    {{
      "topic": "string - what is the trend about",
      "angle": "string - the specific messaging angle or shift",
      "senders": ["organization1", "organization2"],
      "example_subjects": ["subject line 1", "subject line 2"],
      "heat_score": 1-5
    }}
  ],
  "spend_cards": [
    {{
      "title": "string - headline for spend signal",
      "detail": "string - specific detail: geography, dollar amount, race, messaging frame"
    }}
  ],
  "flag_cards": [
    {{
      "severity": "red|amber|green",
      "title": "string - headline",
      "description": "string - what and why it matters"
    }}
  ],
  "stats": {{
    "total_emails": number,
    "trending_topics_count": number,
    "spend_signals_count": number,
    "new_senders_count": number
  }}
}}

Be specific. Use real subject lines. Name actual senders. Include real dollar amounts and district names when present."""

    return prompt


# Legacy placeholder for single-email analysis (if needed in future)
CATEGORIZE_EMAIL_PROMPT = """You are analyzing a political email to categorize its organizational sender.

Email From: {sender}
Subject: {subject}
Body preview: {body}

Respond with ONLY the organization name that appears in the From field. This should be a recognizable PAC, candidate committee, or political organization name — not an email address, not a person's name, just the organization.

If the organization is ambiguous or unclear, respond with: UNRECOGNIZED"""
