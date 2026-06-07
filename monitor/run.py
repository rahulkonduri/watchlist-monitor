"""Entry point: python -m monitor.run"""
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict

import yaml

from .ai_notes import get_ai_notes
from .core import fetch_history, scan  # noqa: F401 (fetch_history re-exported for back-compat)
from .emailer import build_html, send_or_print

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config(path: Path = _CONFIG_PATH) -> Dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> None:
    try:
        cfg = load_config()
    except FileNotFoundError:
        print(f"config.yaml not found at {_CONFIG_PATH}. See README.md for setup.", file=sys.stderr)
        sys.exit(1)

    tickers = cfg.get("tickers") or []
    always_send: bool = bool(cfg.get("always_send_summary", False))

    if not tickers:
        print("No tickers configured. Edit config.yaml and add tickers.", file=sys.stderr)
        sys.exit(0)

    def _progress(ticker: str, result: Dict[str, Any]) -> None:
        status = (
            f"{len(result['alerts'])} alert(s)"
            if not result.get("error")
            else f"ERROR: {result['error']}"
        )
        print(f"Fetching {ticker} … {status}", flush=True)

    results = scan(cfg, tickers, progress=_progress)

    has_alerts = any(r["alerts"] for r in results)

    if not has_alerts and not always_send:
        print("No alerts fired and always_send_summary is false. Nothing to send.")
        return

    ai_notes: Dict[str, str] = {}
    try:
        ai_notes = get_ai_notes(results, cfg)
    except Exception:
        pass

    today = date.today()
    alert_count = sum(len(r["alerts"]) for r in results)
    if has_alerts:
        subject = f"Watchlist Monitor: {alert_count} alert(s) — {today.strftime('%Y-%m-%d')}"
    else:
        subject = f"Watchlist Monitor: Daily Summary — {today.strftime('%Y-%m-%d')}"

    html_body = build_html(results, ai_notes, today)
    send_or_print(subject, html_body)


if __name__ == "__main__":
    main()
