# CloudWalk Monitoring – PoC

A small **FastAPI** service that:
- reads a **CSV** with per-minute counts (`failed`, `denied`, `reversed`);
- computes a **baseline** (mean μ and std σ) and detects anomalies with **Z-score**;
- exposes endpoints and a simple **Chart.js dashboard**.

---

## 1) Prerequisites

- **Python 3.11+**
- Windows (tested) / macOS / Linux
- (Optional) Slack Incoming Webhook URL

---

## 2) Setup (Windows – Command Prompt)

```bat
:: 2.1 create virtual env and install dependencies
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

:: 2.2 configure environment
copy .env.example .env
:: open .env in a text editor and set the values below (see section 3)

:: 2.3 start the API
python -m uvicorn app:app --reload --port 8000
:: API docs: http://127.0.0.1:8000/docs
