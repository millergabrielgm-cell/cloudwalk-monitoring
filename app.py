import os, json
import pandas as pd
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()
CSV_PATH = os.getenv("TX_CSV_PATH", "data/transactions.csv")
K = float(os.getenv("ALERT_K", "3.0"))
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

app = FastAPI(title="Tx Anomaly Monitor (Simple)", version="1.0")

def _map_status(s: str) -> str:
    if s in ("reversed","backend_reversed","refunded"):
        return "reversed"
    if s in ("failed","denied","approved"):
        return s
    return "other"

def compute_baseline(csv_path: str):
    # 1) ler CSV detectando separador e normalizando cabeçalhos
    df = pd.read_csv(csv_path, sep=None, engine="python")
    df.columns = [c.strip().lower().lstrip("\ufeff") for c in df.columns]

    # 2) mapear sinônimos esperados
    if "timestamp" not in df.columns:
        for cand in ("ts", "time", "datetime", "date_time"):
            if cand in df.columns:
                df.rename(columns={cand: "timestamp"}, inplace=True)
                break
    if "status" not in df.columns:
        for cand in ("state", "txn_status"):
            if cand in df.columns:
                df.rename(columns={cand: "status"}, inplace=True)
                break
    if "count" not in df.columns:
        for cand in ("qty", "n", "value"):
            if cand in df.columns:
                df.rename(columns={cand: "count"}, inplace=True)
                break

    # 3) validação amigável
    required = {"timestamp", "status", "count"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Found: {list(df.columns)}")

    # 4) parse robusto de datas (aceita dd/MM/yyyy HH:mm e ISO)
    ts = pd.to_datetime(df["timestamp"], errors="coerce", dayfirst=True)
    if ts.isna().any():
        s = df.loc[ts.isna(), "timestamp"].astype(str)
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            ts_try = pd.to_datetime(s, format=fmt, errors="coerce")
            ts.loc[ts.isna() & ts_try.notna()] = ts_try
    if ts.isna().any():
        bad = df.loc[ts.isna(), "timestamp"].astype(str).head(5).tolist()
        raise ValueError(f"Could not parse some timestamps. Examples: {bad}")

    df["timestamp"] = ts
    df["minute"] = df["timestamp"].dt.floor("min")
    df["stat"] = df["status"].map(_map_status)
    df["count"] = df["count"].astype(int)

    # 5) pivot por minuto
    wide = df.pivot_table(index="minute", columns="stat", values="count", aggfunc="sum").fillna(0)
    for c in ["failed", "denied", "reversed"]:
        if c not in wide.columns:
            wide[c] = 0

    # 6) baseline global e limiar
    mu = {c: float(wide[c].mean()) for c in ["failed", "denied", "reversed"]}
    sd = {c: float(wide[c].std(ddof=1)) for c in ["failed", "denied", "reversed"]}
    thr = {c: (mu[c] + K * sd[c]) if sd[c] > 0 else float("inf") for c in mu}
    return mu, sd, thr


MU, SD, THR = compute_baseline(CSV_PATH)

class MinuteCounts(BaseModel):
    minute: Optional[str] = None
    failed: int = 0
    denied: int = 0
    reversed: int = 0

def maybe_notify_slack(payload: Dict):
    if not SLACK_WEBHOOK:
        return
    try:
        requests.post(
            SLACK_WEBHOOK,
            json={"text": f":rotating_light: Tx alert\n```{json.dumps(payload, indent=2)}```"},
            timeout=5,
        )
    except Exception:
        pass

@app.get("/health")
def health():
    return {"ok": True, "k": K, "csv": CSV_PATH}

@app.post("/alert")
def alert(minute_counts: MinuteCounts):
    x = minute_counts.dict()
    result, any_alert = {}, False
    for s in ["failed","denied","reversed"]:
        val, mu, sd, thr = x.get(s, 0), MU[s], SD[s], THR[s]
        z = None if sd == 0 else (val - mu) / sd
        is_alert = val > thr
        result[s] = {"value": val, "mu": mu, "sigma": sd, "threshold": thr, "k": K, "z": z, "alert": is_alert}
        any_alert |= is_alert
    payload = {"minute": x.get("minute"), "result": result, "any_alert": any_alert}
    if any_alert:
        maybe_notify_slack(payload)
    return payload

@app.post("/reload-baseline")
def reload_baseline():
    global MU, SD, THR
    MU, SD, THR = compute_baseline(CSV_PATH)
    return {"reloaded": True, "k": K, "csv": CSV_PATH}
