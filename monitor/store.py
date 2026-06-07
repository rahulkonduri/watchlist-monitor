"""Persistence for the web UI — SQLite locally, PostgreSQL when hosted.

Backend selection is automatic:
  * If the ``DATABASE_URL`` env var is set (e.g. on GCP Cloud Run pointing at
    Cloud SQL), PostgreSQL is used via psycopg2.
  * Otherwise it falls back to a local SQLite file (``WATCHLIST_DB`` or
    ``watchlist.db``).

Cloud Run has an ephemeral filesystem, so SQLite there would lose data on every
restart — that is why a managed Postgres is required for hosting. The SQL is kept
deliberately simple and portable; the only per-backend differences (parameter
placeholder, auto-increment, RETURNING) are handled by the thin helpers below.

A fresh connection is opened per operation so it is safe to call from FastAPI
worker threads and APScheduler.

Tables:
  holdings(id, ticker, shares, cost_basis, purchased_on)
  interests(id, kind['ticker'|'theme'], value)
  settings(key, value)   -- value is JSON
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .themes import expand_interests

_DEFAULT_DB = Path(__file__).parent.parent / "watchlist.db"
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = bool(_DATABASE_URL)

if USE_PG:  # imported lazily so local SQLite users need no psycopg2 installed
    import psycopg2
    import psycopg2.extras

DEFAULT_SETTINGS: Dict[str, Any] = {
    "triggers": {
        "daily_move_pct": 3.0,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "ma_short": 50,
        "ma_long": 200,
    },
    "ai_analysis": {
        "enabled": False,
        "question": "What recent news themes or sector backdrop are most relevant to this stock right now?",
    },
    "always_send_summary": True,
    "schedule": {"enabled": False, "hour": 16, "minute": 30},
}


def db_path() -> Path:
    return Path(os.environ.get("WATCHLIST_DB", str(_DEFAULT_DB)))


# ── Backend-portable helpers ─────────────────────────────────────────────────

def _q(sql: str) -> str:
    """Translate the SQLite ``?`` placeholder to Postgres ``%s`` when needed."""
    return sql.replace("?", "%s") if USE_PG else sql


@contextmanager
def _cursor() -> Iterator[Any]:
    """Yield a cursor whose rows behave like dicts, committing/closing on exit."""
    if USE_PG:
        conn = psycopg2.connect(_DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = sqlite3.connect(str(db_path()))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _insert(cur: Any, sql: str, params: tuple) -> int:
    """Run an INSERT and return the new row id, portably."""
    if USE_PG:
        cur.execute(_q(sql) + " RETURNING id", params)
        return int(cur.fetchone()["id"])
    cur.execute(sql, params)
    return int(cur.lastrowid)


def init_db() -> None:
    """Create tables if missing, then seed from config.yaml on first run."""
    if USE_PG:
        ddl = [
            """CREATE TABLE IF NOT EXISTS holdings (
                   id SERIAL PRIMARY KEY,
                   ticker TEXT NOT NULL,
                   shares DOUBLE PRECISION NOT NULL,
                   cost_basis DOUBLE PRECISION NOT NULL,
                   purchased_on TEXT
               )""",
            """CREATE TABLE IF NOT EXISTS interests (
                   id SERIAL PRIMARY KEY,
                   kind TEXT NOT NULL,
                   value TEXT NOT NULL
               )""",
            """CREATE TABLE IF NOT EXISTS settings (
                   key TEXT PRIMARY KEY,
                   value TEXT NOT NULL
               )""",
        ]
        with _cursor() as cur:
            for stmt in ddl:
                cur.execute(stmt)
    else:
        with _cursor() as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    shares REAL NOT NULL,
                    cost_basis REAL NOT NULL,
                    purchased_on TEXT
                );
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
    _seed_if_empty()


# ── Settings ───────────────────────────────────────────────────────────────

def get_settings() -> Dict[str, Any]:
    """Return merged settings (defaults overlaid with stored values)."""
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))  # deep copy
    with _cursor() as cur:
        cur.execute("SELECT key, value FROM settings")
        rows = cur.fetchall()
    for row in rows:
        merged[row["key"]] = json.loads(row["value"])
    return merged


def update_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow-merge top-level keys; nested dicts (triggers, ai_analysis) merge one level."""
    current = get_settings()
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(current.get(key), dict):
            current[key].update(val)
        else:
            current[key] = val
    with _cursor() as cur:
        for key, val in current.items():
            cur.execute(
                _q(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
                ),
                (key, json.dumps(val)),
            )
    return current


# ── Holdings ───────────────────────────────────────────────────────────────

def list_holdings() -> List[Dict[str, Any]]:
    with _cursor() as cur:
        cur.execute("SELECT * FROM holdings ORDER BY ticker")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def add_holding(ticker: str, shares: float, cost_basis: float, purchased_on: Optional[str] = None) -> Dict[str, Any]:
    with _cursor() as cur:
        hid = _insert(
            cur,
            "INSERT INTO holdings(ticker, shares, cost_basis, purchased_on) VALUES(?,?,?,?)",
            (ticker.strip().upper(), float(shares), float(cost_basis), purchased_on),
        )
        cur.execute(_q("SELECT * FROM holdings WHERE id=?"), (hid,))
        row = cur.fetchone()
    return dict(row)


def update_holding(hid: int, **fields: Any) -> Optional[Dict[str, Any]]:
    allowed = {"ticker", "shares", "cost_basis", "purchased_on"}
    sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not sets:
        return get_holding(hid)
    if "ticker" in sets:
        sets["ticker"] = str(sets["ticker"]).strip().upper()
    assignments = ", ".join(f"{k}=?" for k in sets)
    with _cursor() as cur:
        cur.execute(_q(f"UPDATE holdings SET {assignments} WHERE id=?"), (*sets.values(), hid))
        cur.execute(_q("SELECT * FROM holdings WHERE id=?"), (hid,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_holding(hid: int) -> Optional[Dict[str, Any]]:
    with _cursor() as cur:
        cur.execute(_q("SELECT * FROM holdings WHERE id=?"), (hid,))
        row = cur.fetchone()
    return dict(row) if row else None


def delete_holding(hid: int) -> bool:
    with _cursor() as cur:
        cur.execute(_q("DELETE FROM holdings WHERE id=?"), (hid,))
        return cur.rowcount > 0


# ── Interests ──────────────────────────────────────────────────────────────

def list_interests() -> List[Dict[str, Any]]:
    with _cursor() as cur:
        cur.execute("SELECT * FROM interests ORDER BY kind, value")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def add_interest(kind: str, value: str) -> Dict[str, Any]:
    kind = kind.strip().lower()
    value = value.strip()
    if kind == "ticker":
        value = value.upper()
    else:
        value = value.lower()
    with _cursor() as cur:
        # avoid duplicates
        cur.execute(_q("SELECT * FROM interests WHERE kind=? AND value=?"), (kind, value))
        existing = cur.fetchone()
        if existing:
            return dict(existing)
        iid = _insert(cur, "INSERT INTO interests(kind, value) VALUES(?,?)", (kind, value))
        cur.execute(_q("SELECT * FROM interests WHERE id=?"), (iid,))
        row = cur.fetchone()
    return dict(row)


def delete_interest(iid: int) -> bool:
    with _cursor() as cur:
        cur.execute(_q("DELETE FROM interests WHERE id=?"), (iid,))
        return cur.rowcount > 0


# ── Derived config / tickers ─────────────────────────────────────────────────

def watchlist_tickers() -> List[str]:
    """Tickers from interests (explicit + theme expansions) merged with holdings."""
    syms = expand_interests(list_interests())
    seen = {s for s in syms}
    for h in list_holdings():
        t = (h["ticker"] or "").upper()
        if t and t not in seen:
            seen.add(t)
            syms.append(t)
    return syms


def build_cfg() -> Dict[str, Any]:
    """Reconstruct the cfg dict shape that triggers/ai_notes/core expect."""
    s = get_settings()
    return {
        "tickers": watchlist_tickers(),
        "triggers": s["triggers"],
        "ai_analysis": s["ai_analysis"],
        "always_send_summary": s["always_send_summary"],
        "schedule": s["schedule"],
    }


# ── Seed + export bridge to config.yaml ──────────────────────────────────────

def _seed_if_empty() -> None:
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM interests")
        n_int = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM settings")
        n_set = cur.fetchone()["c"]
    if n_int or n_set:
        return
    try:
        import yaml

        with open(_CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}

    for t in (cfg.get("tickers") or []):
        add_interest("ticker", str(t))

    patch: Dict[str, Any] = {}
    if isinstance(cfg.get("triggers"), dict):
        patch["triggers"] = cfg["triggers"]
    if isinstance(cfg.get("ai_analysis"), dict):
        patch["ai_analysis"] = cfg["ai_analysis"]
    if "always_send_summary" in cfg:
        patch["always_send_summary"] = bool(cfg["always_send_summary"])
    if patch:
        update_settings(patch)


def export_to_yaml(path: Optional[Path] = None) -> str:
    """Write current interests/settings back to config.yaml for the Actions cron."""
    import yaml

    path = path or _CONFIG_PATH
    s = get_settings()
    doc = {
        "tickers": watchlist_tickers(),
        "triggers": s["triggers"],
        "always_send_summary": s["always_send_summary"],
        "ai_analysis": s["ai_analysis"],
    }
    text = yaml.safe_dump(doc, sort_keys=False, default_flow_style=False)
    with open(path, "w") as f:
        f.write("# Generated by the watchlist-monitor UI (Export to config.yaml)\n")
        f.write(text)
    return str(path)
