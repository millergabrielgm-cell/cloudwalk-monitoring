# Cloudwalk Monitoring – PoC

Small FastAPI service that receives per-minute transaction counts
(`failed`, `denied`, `reversed`), computes a baseline (mean & std-dev) from a CSV,
and flags anomalies using a Z-score. It can optionally notify a Slack channel.

---

## Why this exists

- **Baseline from CSV:** at startup we read a CSV with per-minute counts, normalize the status,
  and compute µ (mean) and σ (stddev) for each metric.
- **Score-based alert:** for each incoming minute we compute `z = (value - µ) / σ`
  and compare with a tunable threshold **K** (default 3.0).
- **Optional Slack:** if `SLACK_WEBHOOK_URL` is set, alerts are posted to Slack.

---

## Requirements

- Python 3.11+
- Windows (tested) / Mac / Linux
- (Optional) Slack Incoming Webhook URL

---

## Quick start

```bash
# 1) create venv and install
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 2) environment
copy .env.example .env
# edit .env to adjust CSV path, ALERT_K and (optionally) SLACK_WEBHOOK_URL

# 3) run the API
uvicorn app:app --reload --port 8000
# docs: http://127.0.0.1:8000/docs
