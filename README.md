# CloudWalk Monitoring – PoC

Small FastAPI service that receives per-minute transaction counts (**failed / denied / reversed**),
computes a baseline (mean & std) from a CSV, and flags anomalies with a Z-score.
It also supports optional Slack webhook notifications.

## Quick start (Windows)

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env   # adjust CSV path/Slack if needed
uvicorn app:app --reload --port 8000
