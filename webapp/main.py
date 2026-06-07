"""FastAPI backend for the watchlist-monitor UI.

Run:  uvicorn webapp.main:app --reload
Then open http://127.0.0.1:8000

Reuses the existing monitor pipeline (core.scan, triggers.evaluate, emailer,
ai_notes) and the SQLite store. Decision-support only — never places trades.
"""
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from monitor import store
from monitor.ai_notes import get_ai_notes
from monitor.assessment import assess
from monitor.triggers import evaluate
from monitor.core import fetch_history, fetch_many, scan
from monitor.indicators import daily_pct_change, sma, wilder_rsi
from monitor.emailer import build_html, send_or_print
from monitor.portfolio import compute_position, summarize
from monitor.screener import build_ideas
from monitor.themes import available_themes
from monitor.universe import get_index, index_meta

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Watchlist Monitor", version="1.0")

# ── Scheduler (in-app daily job) ─────────────────────────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler

    _scheduler: Optional[BackgroundScheduler] = BackgroundScheduler(daemon=True)
except Exception:  # apscheduler missing — UI still works, no auto-email
    _scheduler = None

_JOB_ID = "daily_report"


def _run_daily_report() -> None:
    cfg = store.build_cfg()
    results = scan(cfg, refresh=True)
    has_alerts = any(r["alerts"] for r in results)
    if not has_alerts and not cfg.get("always_send_summary", True):
        return
    ai_notes: Dict[str, str] = {}
    try:
        ai_notes = get_ai_notes(results, cfg)
    except Exception:
        pass
    today = date.today()
    alert_count = sum(len(r["alerts"]) for r in results)
    subject = (
        f"Watchlist Monitor: {alert_count} alert(s) — {today:%Y-%m-%d}"
        if has_alerts
        else f"Watchlist Monitor: Daily Summary — {today:%Y-%m-%d}"
    )
    send_or_print(subject, build_html(results, ai_notes, today))


def _reschedule() -> None:
    if _scheduler is None:
        return
    sched = store.get_settings().get("schedule", {})
    if _scheduler.get_job(_JOB_ID):
        _scheduler.remove_job(_JOB_ID)
    if sched.get("enabled"):
        _scheduler.add_job(
            _run_daily_report,
            "cron",
            day_of_week="mon-fri",
            hour=int(sched.get("hour", 16)),
            minute=int(sched.get("minute", 30)),
            id=_JOB_ID,
        )


@app.on_event("startup")
def _startup() -> None:
    store.init_db()
    if _scheduler is not None and not _scheduler.running:
        _scheduler.start()
    _reschedule()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _enrich_rows(results: List[Dict[str, Any]], cfg: Dict[str, Any], ai_notes: Dict[str, str]) -> List[Dict[str, Any]]:
    held = {h["ticker"].upper() for h in store.list_holdings()}
    rows = []
    for r in results:
        rows.append(
            {
                **r,
                "held": r["ticker"].upper() in held,
                "assessment": assess(r, cfg=cfg),
                "ai_note": ai_notes.get(r["ticker"]),
            }
        )
    return rows


# ── Models ───────────────────────────────────────────────────────────────────

class HoldingIn(BaseModel):
    ticker: str
    shares: float
    cost_basis: float
    purchased_on: Optional[str] = None


class HoldingPatch(BaseModel):
    ticker: Optional[str] = None
    shares: Optional[float] = None
    cost_basis: Optional[float] = None
    purchased_on: Optional[str] = None


class InterestIn(BaseModel):
    kind: str  # 'ticker' | 'theme'
    value: str


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard(refresh: bool = Query(False)) -> Dict[str, Any]:
    cfg = store.build_cfg()
    results = scan(cfg, refresh=refresh)
    ai_notes: Dict[str, str] = {}
    ai_enabled = bool(cfg.get("ai_analysis", {}).get("enabled"))
    if ai_enabled:
        try:
            ai_notes = get_ai_notes(results, cfg)
        except Exception:
            ai_notes = {}
    rows = _enrich_rows(results, cfg, ai_notes)
    return {
        "as_of": datetime.now().isoformat(timespec="seconds"),
        "rows": rows,
        "ai_enabled": ai_enabled,
        "ai_active": bool(ai_notes),
        "counts": {
            "tickers": len(rows),
            "alerts": sum(len(r["alerts"]) for r in rows),
        },
    }


# ── Daily Ideas (screener) ───────────────────────────────────────────────────

@app.get("/api/ideas")
def ideas(refresh: bool = Query(False)) -> Dict[str, Any]:
    cfg = store.build_cfg()
    results = scan(cfg, refresh=refresh)
    ai_notes: Dict[str, str] = {}
    if cfg.get("ai_analysis", {}).get("enabled"):
        try:
            ai_notes = get_ai_notes(results, cfg)
        except Exception:
            ai_notes = {}
    data = build_ideas(results, cfg, ai_notes)
    data["as_of"] = datetime.now().isoformat(timespec="seconds")
    return data


# ── Market scan (beyond the watchlist — top US/India indexes) ─────────────────

@app.get("/api/universe")
def universe() -> Dict[str, Any]:
    return {"indexes": index_meta()}


@app.get("/api/market-scan")
def market_scan(index: str = Query(...), refresh: bool = Query(False)) -> Dict[str, Any]:
    try:
        idx = get_index(index)
    except KeyError:
        raise HTTPException(404, f"unknown index '{index}'")

    cfg = store.build_cfg()
    tickers = idx["tickers"]
    histories = fetch_many(tickers, refresh=refresh)
    results = scan(cfg, tickers, histories=histories)
    # No AI notes here: a 100-ticker scan would be too many API calls.
    data = build_ideas(results, cfg, ai_notes={}, top_n=8, group_limit=15)
    data["as_of"] = datetime.now().isoformat(timespec="seconds")
    data["index"] = {
        "key": index, "name": idx["name"], "currency": idx["currency"],
        "symbol": idx["symbol"], "count": len(tickers),
    }
    return data


# ── Portfolio ────────────────────────────────────────────────────────────────

@app.get("/api/portfolio")
def get_portfolio(refresh: bool = Query(False)) -> Dict[str, Any]:
    holdings = store.list_holdings()
    cfg = store.build_cfg()
    results = scan(cfg, [h["ticker"] for h in holdings], refresh=refresh) if holdings else []
    prices = {r["ticker"].upper(): r.get("price") for r in results}
    positions = [compute_position(h, prices.get(h["ticker"].upper())) for h in holdings]
    return {"positions": positions, "summary": summarize(positions)}


@app.get("/api/holdings")
def list_holdings() -> List[Dict[str, Any]]:
    return store.list_holdings()


@app.post("/api/holdings")
def create_holding(body: HoldingIn) -> Dict[str, Any]:
    if not body.ticker.strip():
        raise HTTPException(400, "ticker is required")
    return store.add_holding(body.ticker, body.shares, body.cost_basis, body.purchased_on)


@app.put("/api/holdings/{hid}")
def edit_holding(hid: int, body: HoldingPatch) -> Dict[str, Any]:
    updated = store.update_holding(hid, **body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(404, "holding not found")
    return updated


@app.delete("/api/holdings/{hid}")
def remove_holding(hid: int) -> Dict[str, Any]:
    if not store.delete_holding(hid):
        raise HTTPException(404, "holding not found")
    return {"deleted": hid}


# ── Interests ────────────────────────────────────────────────────────────────

@app.get("/api/interests")
def get_interests() -> Dict[str, Any]:
    return {"interests": store.list_interests(), "available_themes": available_themes()}


@app.post("/api/interests")
def create_interest(body: InterestIn) -> Dict[str, Any]:
    if body.kind not in ("ticker", "theme"):
        raise HTTPException(400, "kind must be 'ticker' or 'theme'")
    if not body.value.strip():
        raise HTTPException(400, "value is required")
    return store.add_interest(body.kind, body.value)


@app.delete("/api/interests/{iid}")
def remove_interest(iid: int) -> Dict[str, Any]:
    if not store.delete_interest(iid):
        raise HTTPException(404, "interest not found")
    return {"deleted": iid}


# ── Settings ─────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def read_settings() -> Dict[str, Any]:
    import os

    s = store.get_settings()
    s["_env"] = {
        "openai_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "smtp_configured": all(
            os.environ.get(k) for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_TO")
        ),
    }
    return s


@app.put("/api/settings")
def write_settings(patch: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    patch.pop("_env", None)
    updated = store.update_settings(patch)
    _reschedule()
    return updated


# ── Email ────────────────────────────────────────────────────────────────────

@app.post("/api/email/preview")
def email_preview(refresh: bool = Query(False)) -> Dict[str, Any]:
    cfg = store.build_cfg()
    results = scan(cfg, refresh=refresh)
    ai_notes: Dict[str, str] = {}
    if cfg.get("ai_analysis", {}).get("enabled"):
        try:
            ai_notes = get_ai_notes(results, cfg)
        except Exception:
            ai_notes = {}
    return {"html": build_html(results, ai_notes, date.today())}


@app.post("/api/email/send")
def email_send(refresh: bool = Query(True)) -> Dict[str, Any]:
    _run_daily_report()
    return {"status": "sent (or printed to server stdout if SMTP not configured)"}


# ── Scheduled job trigger (for GCP Cloud Scheduler) ──────────────────────────
# On Cloud Run the in-app APScheduler cannot run reliably (instances scale to
# zero between requests), so the daily report is driven by an external Cloud
# Scheduler HTTP call hitting this endpoint. Protected by a shared secret.

@app.post("/api/job/run-daily")
def run_daily_job(x_job_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    import os

    expected = os.environ.get("JOB_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "JOB_TOKEN is not configured on the server")
    if x_job_token != expected:
        raise HTTPException(401, "invalid or missing X-Job-Token header")
    _run_daily_report()
    return {"status": "daily report run", "as_of": datetime.now().isoformat(timespec="seconds")}


# ── Ticker Inspector ─────────────────────────────────────────────────────────

@app.get("/api/ticker/{symbol}")
def inspect_ticker(symbol: str, refresh: bool = Query(False)) -> Dict[str, Any]:
    """Full single-ticker deep-dive: indicators, chart series, assessment, AI note."""
    symbol = symbol.strip().upper()
    cfg = store.build_cfg()

    try:
        hist = fetch_history(symbol, use_cache=not refresh)
    except Exception as exc:
        raise HTTPException(502, f"Could not fetch data for {symbol}: {exc}")

    if hist is None or hist.empty:
        raise HTTPException(404, f"No data found for ticker '{symbol}'")

    closes = hist["Close"].dropna()
    if len(closes) < 2:
        raise HTTPException(404, f"Insufficient data for ticker '{symbol}'")

    result = evaluate(symbol, hist, cfg)
    assessment_data = assess(result, cfg=cfg)

    # Build chart series — last 90 trading days (or all if fewer)
    n = min(90, len(closes))
    recent_closes = closes.iloc[-n:]
    dates = [str(d.date()) if hasattr(d, "date") else str(d) for d in recent_closes.index]
    prices_list = [round(float(v), 4) for v in recent_closes.values]

    # Indicator series over the same window
    full_sma50  = sma(closes, 50)
    full_sma200 = sma(closes, 200)
    full_rsi    = wilder_rsi(closes, 14)

    def _ser(series):
        vals = series.iloc[-n:]
        return [round(float(v), 4) if not pd.isna(v) else None for v in vals]

    # SMA relationship label
    last_sma50  = full_sma50.dropna().iloc[-1]  if len(full_sma50.dropna())  else None
    last_sma200 = full_sma200.dropna().iloc[-1] if len(full_sma200.dropna()) else None
    sma_relationship = None
    if last_sma50 is not None and last_sma200 is not None:
        if last_sma50 > last_sma200:
            sma_relationship = "Price above both MAs — long-term uptrend context"
        else:
            sma_relationship = "Short MA below long MA — long-term downtrend context"

    # AI note (optional)
    ai_note = None
    if cfg.get("ai_analysis", {}).get("enabled"):
        try:
            notes = get_ai_notes([result], cfg)
            ai_note = notes.get(symbol)
        except Exception:
            pass

    return {
        "symbol": symbol,
        "as_of": datetime.now().isoformat(timespec="seconds"),
        "snapshot": result,
        "assessment": assessment_data,
        "ai_note": ai_note,
        "sma_relationship": sma_relationship,
        "current": {
            "sma50":  round(float(last_sma50),  2) if last_sma50  is not None else None,
            "sma200": round(float(last_sma200), 2) if last_sma200 is not None else None,
        },
        "chart": {
            "dates":   dates,
            "prices":  prices_list,
            "sma50":   _ser(full_sma50),
            "sma200":  _ser(full_sma200),
            "rsi":     _ser(full_rsi),
        },
    }


# ── Export bridge ────────────────────────────────────────────────────────────

@app.post("/api/export-config")
def export_config() -> Dict[str, Any]:
    path = store.export_to_yaml()
    return {"path": path}


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"status": "ok", "db": "postgres" if store.USE_PG else "sqlite"}


# ── Static frontend ──────────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / "index.html"))


app.mount("/", StaticFiles(directory=str(_STATIC_DIR)), name="static")
