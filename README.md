# PAC Intel Digest Pipeline

Automated daily political intelligence digest that reads a Gmail inbox, analyzes emails with Claude AI, generates fresh HTML, deploys to GitHub Pages, and sends a notification email.

**Schedule**: 7am ET every weekday (Monday-Friday)  
**Status page**: https://alittleagency.github.io/vncs-email-digest  
**Notification to**: email-tech@vncs.io

---

## Setup Instructions

### 1. Create the GitHub Repository

```bash
gh repo create vncs-email-digest --public --source=. --remote=origin --push
```

This creates a public repo at `alittleagency/vncs-email-digest`.

### 2. Enable GitHub Pages

In the repository settings:
1. Go to **Settings** → **Pages**
2. Set **Source** to `Deploy from a branch`
3. Select **main** branch and **/ (root)** folder
4. Save

GitHub Pages will be live at: `https://alittleagency.github.io/vncs-email-digest`

### 3. Create Gmail OAuth2 Credentials

The pipeline uses **installed app** OAuth2 (user-facing flow), not a service account.

**Step 1: Create a Google Cloud project**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (name: "PAC Intel Digest" or similar)
3. Enable the **Gmail API**:
   - Go to **APIs & Services** → **Library**
   - Search for "Gmail API"
   - Click **Enable**

**Step 2: Create OAuth2 credentials**
1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Choose **Desktop application**
4. Name it "PAC Intel Digest"
5. Click **Create**
6. Download the JSON file and save as `client_secret.json`

**Step 3: Generate credentials during first run**
When you run the pipeline for the first time locally, it will:
1. Open a browser window asking you to authorize Gmail access
2. Create `gmail_credentials.json` with your token
3. This file is git-ignored and never pushed to the repo

**Step 4: Add credentials to GitHub**
1. Copy the contents of `client_secret.json`
2. Go to repo **Settings** → **Secrets and variables** → **Actions**
3. Create a new secret `GMAIL_CREDENTIALS` with the JSON contents
4. Also save `client_secret.json` locally (you'll need it for local testing)

### 4. Get Anthropic API Key

1. Sign in to [Anthropic Console](https://console.anthropic.com/)
2. Go to **API Keys**
3. Create a new API key
4. Copy it

**Add to GitHub Secrets**:
1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Create a new secret `ANTHROPIC_API_KEY` with your key

### 5. Create a GitHub Personal Access Token (PAT)

The pipeline needs write access to push HTML updates to the repo.

1. Go to GitHub **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token**
3. Give it a name: "PAC Intel Digest"
4. Grant scopes: `repo` (full control of private/public repos)
5. Copy the token

**Add to GitHub Secrets**:
1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Create a new secret `GH_PAT` with your token

### 6. Create a Gmail App Password

For the pipeline to send emails via Gmail SMTP, you need an app-specific password (not your account password).

**If you have 2-Step Verification enabled** (recommended):
1. Go to [Google Account](https://myaccount.google.com/)
2. Go to **Security** → **App passwords**
3. Select **Mail** and **Windows Computer** (or your device)
4. Google will generate a 16-character app password
5. Copy it

**If you don't have 2-Step Verification**:
1. Enable it first (recommended for security)
2. Then follow the steps above

**Add to GitHub Secrets**:
1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Create a new secret `GMAIL_APP_PASSWORD` with the 16-character password

### 7. Update Configuration

Edit `config.py` and update:
- Line 15: `GMAIL_ACCOUNT` — set to your Gmail address (e.g., `monitoring@gmail.com`)

All other settings are pre-configured.

### 8. Test Locally (Optional)

Before deploying, test the pipeline locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Copy client_secret.json to the repo root
cp ~/Downloads/client_secret.json .

# Run the pipeline
python run_digest.py
```

On first run:
1. A browser window will open asking you to authorize Gmail access
2. The pipeline will generate `gmail_credentials.json`
3. It will pull emails, analyze with Claude, generate HTML, and commit to the repo

### 9. First Automated Run

The workflow is scheduled to run at 7am ET every weekday. To trigger it manually for testing:

1. Go to the repo **Actions** tab
2. Click **Daily PAC Intel Digest** workflow
3. Click **Run workflow** → **Run workflow**

The workflow will run and you can watch the logs in real-time.

---

## How It Works

### Pipeline Flow

1. **Email Fetch** (Gmail API)
   - Connects to the Gmail inbox (OAuth2)
   - Pulls all unread emails from the last 24 hours
   - Extracts: sender organization, subject, body preview, timestamp

2. **Sender Categorization** (senders.json lookup)
   - Matches sender organization names against a lookup table
   - Categories: `dside` (Democratic), `watch` (Republican), `news` (industry)
   - Tracks unrecognized senders as "new senders"

3. **Claude Analysis** (Anthropic API)
   - Sends all email data to Claude Sonnet
   - Claude identifies: messaging trends, GOP spend signals, flags
   - Returns structured JSON with cards and stats

4. **HTML Generation** (BeautifulSoup injection)
   - Reads the template (index.html)
   - Injects: trend cards, spend cards, flag cards, stats, email list
   - Updates datestamp

5. **GitHub Deployment** (GitPython)
   - Clones the repo
   - Writes updated index.html
   - Commits with timestamp message
   - Pushes to main branch
   - GitHub Pages auto-updates

6. **Email Notification** (Gmail SMTP)
   - Sends notification to email-tech@vncs.io
   - Subject: "PAC Intel Digest — [Date]"
   - Body: Link to the live digest
   - On error: Sends error notification with details

### Files

- **run_digest.py** — Main pipeline orchestrator
- **config.py** — Configuration (Gmail, Claude, GitHub, Email settings)
- **claude_prompt.py** — Claude API prompt template
- **senders.json** — Sender organization lookup table
- **index.html** — HTML template with all CSS and structure
- **requirements.txt** — Python dependencies
- **.github/workflows/daily_digest.yml** — GitHub Actions scheduler

---

## Monitoring and Troubleshooting

### Check the Live Digest

After the workflow runs, the digest is live at:
```
https://alittleagency.github.io/vncs-email-digest
```

### Monitor Workflow Runs

1. Go to repo **Actions** tab
2. Click the latest **Daily PAC Intel Digest** run
3. View logs for each step
4. If failed, check error messages and logs

### Common Issues

**"No unread emails found"**
- Normal if the Gmail account hasn't received emails in 24 hours
- Workflow still completes successfully

**"Gmail authentication failed"**
- Check that `GMAIL_CREDENTIALS` secret is valid JSON
- Ensure Gmail account hasn't been accessed from unusual locations
- Log in to Gmail account in a browser to verify it's accessible

**"Claude API error"**
- Check that `ANTHROPIC_API_KEY` is valid
- Verify you have API credits available
- Check error message in workflow logs for specific issue

**"GitHub push failed"**
- Verify `GH_PAT` token has `repo` scope
- Token may have expired (GitHub resets tokens after a period)
- Check that the repo exists and is public

**"Email send failed"**
- Verify `GMAIL_APP_PASSWORD` is the 16-character app password, not account password
- 2-Step Verification must be enabled on the Gmail account
- Check that `GMAIL_ACCOUNT` in config.py matches the account sending emails

### Manual Error Testing

To test error handling, trigger the workflow and temporarily set a wrong API key:

1. Go to repo **Settings** → **Secrets**
2. Edit `ANTHROPIC_API_KEY` to an invalid value
3. Run the workflow manually
4. It should send an error email to email-tech@vncs.io

---

## Adding More Senders

As new political organizations send emails, update `senders.json` to categorize them:

```json
{
  "dside": ["Existing senders...", "New D PAC Name"],
  "watch": ["Existing senders...", "New R PAC Name"],
  "news": ["Existing senders..."]
}
```

Commit and push. The next run will use the updated list.

---

## Customization

### Change the Schedule

Edit `.github/workflows/daily_digest.yml`, line 8:
```yaml
- cron: '0 12 * * 1-5'  # Change this
```

Cron format: `minute hour day month day-of-week`
- `0 12 * * 1-5` = 12pm UTC (7am ET), Mon-Fri
- `0 8 * * *` = 8am UTC (3am ET), every day
- `0 */6 * * *` = every 6 hours

### Change Email Recipient

Edit `config.py`, line 59:
```python
EMAIL_TO = "new-recipient@example.com"
```

### Adjust Email Lookback Window

Edit `config.py`, line 19:
```python
GMAIL_LOOKBACK_HOURS = 48  # Get emails from last 48 hours instead of 24
```

---

## Security Notes

- **Gmail credentials** (`gmail_credentials.json`) are never committed (in .gitignore)
- **Secrets** (GMAIL_CREDENTIALS, API keys, tokens) are stored securely in GitHub
- **PAT token** has minimal required scope (repo access only)
- All external API calls use HTTPS
- No sensitive data is logged to workflow logs (errors redact API keys)

---

## Support

For issues or questions:
1. Check the workflow logs (Actions tab)
2. Review error messages in the notification email
3. Verify all secrets are set correctly
4. Test locally with `python run_digest.py`

---

## License

Internal use only. Part of the A Little Agency PAC Intel service.
