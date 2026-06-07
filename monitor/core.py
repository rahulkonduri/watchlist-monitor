"""Shared scan pipeline reused by the CLI/cron (run.py) and the web app.

Keeps the fetch -> evaluate loop in one place with a small in-process cache so
the UI can call it repeatedly without hammering yfinance.
"""
import time
import warnings
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

# yfinance internals emit noisy pandas deprecation warnings; keep output clean.
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Timestamp.utcnow.*")

import yfinance as yf

from .triggers import evaluate

_FETCH_DAYS = 400  # ~13 months; enough for a 200-day MA with buffer
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

# ticker -> (timestamp, DataFrame)
_HIST_CACHE: Dict[str, Any] = {}


def fetch_history(ticker: str, use_cache: bool = True) -> Any:
    """Fetch ~13 months of daily OHLC for a ticker, with a 15-min TTL cache."""
    now = time.time()
    if use_cache:
        cached = _HIST_CACHE.get(ticker)
        if cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

    start = (datetime.now() - timedelta(days=_FETCH_DAYS)).strftime("%Y-%m-%d")
    hist = yf.Ticker(ticker).history(start=start)
    _HIST_CACHE[ticker] = (now, hist)
    return hist


def _extract(data: Any, ticker: str, n_tickers: int) -> Any:
    """Pull a single ticker's OHLC frame out of a yf.download result."""
    if data is None or len(data) == 0:
        return None
    try:
        df = data if n_tickers == 1 else data[ticker]
        if df is None or "Close" not in df.columns:
            return None
        df = df.dropna(how="all")
        return df if len(df) else None
    except Exception:
        return None


def fetch_many(tickers, refresh: bool = False) -> Dict[str, Any]:
    """Bulk-fetch histories for many tickers in one yf.download call (fast).

    Returns {ticker: DataFrame|None}. Honors and fills the 15-min cache.
    """
    now = time.time()
    out: Dict[str, Any] = {}
    to_fetch = []
    for t in tickers:
        cached = _HIST_CACHE.get(t)
        if (not refresh) and cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS:
            out[t] = cached[1]
        else:
            to_fetch.append(t)

    if to_fetch:
        start = (datetime.now() - timedelta(days=_FETCH_DAYS)).strftime("%Y-%m-%d")
        try:
            data = yf.download(
                to_fetch, start=start, group_by="ticker",
                threads=True, progress=False, auto_adjust=True,
            )
        except Exception:
            data = None
        for t in to_fetch:
            df = _extract(data, t, len(to_fetch))
            out[t] = df
            if df is not None:
                _HIST_CACHE[t] = (now, df)
    return out


def clear_cache() -> None:
    _HIST_CACHE.clear()


def _error_result(ticker: str, message: str) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "price": None,
        "change_pct": None,
        "rsi": None,
        "ma_cross": None,
        "alerts": [],
        "error": message,
    }


def scan(
    cfg: Dict[str, Any],
    tickers: Optional[List[str]] = None,
    *,
    refresh: bool = False,
    histories: Optional[Dict[str, Any]] = None,
    progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> List[Dict[str, Any]]:
    """Fetch + evaluate each ticker. One bad ticker never aborts the rest.

    Args:
        cfg:       config dict (see triggers.evaluate / ai_notes.get_ai_notes).
        tickers:   explicit ticker list; falls back to cfg["tickers"].
        refresh:   bypass the history cache when True.
        histories: optional {ticker: DataFrame} from fetch_many — when provided,
                   no per-ticker fetching happens (used by the market scanner).
        progress:  optional callback(ticker, result) for streaming/logging.
    """
    syms = tickers if tickers is not None else (cfg.get("tickers") or [])
    results: List[Dict[str, Any]] = []
    for ticker in syms:
        try:
            if histories is not None:
                hist = histories.get(ticker)
            else:
                hist = fetch_history(ticker, use_cache=not refresh)
            result = evaluate(ticker, hist, cfg)
        except Exception as exc:  # network / yfinance failure
            result = _error_result(ticker, str(exc))
        if progress is not None:
            progress(ticker, result)
        results.append(result)
    return results
