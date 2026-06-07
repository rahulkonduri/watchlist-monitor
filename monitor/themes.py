"""Curated theme/sector -> representative tickers mapping.

This is a deliberately small, hand-picked shortcut so a user can express an
'interest' as a theme (e.g. "ai") rather than enumerating tickers. It is NOT an
exhaustive or rebalanced index — just a convenience starting point.
"""
from typing import Any, Dict, Iterable, List, Set

THEME_TICKERS: Dict[str, List[str]] = {
    "ai": ["NVDA", "MSFT", "GOOGL", "META", "PLTR"],
    "semiconductors": ["NVDA", "AMD", "TSM", "AVGO", "ASML"],
    "big-tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    "energy": ["XOM", "CVX", "COP", "SLB"],
    "banks": ["JPM", "BAC", "WFC", "GS"],
    "ev": ["TSLA", "RIVN", "GM", "F"],
    "healthcare": ["UNH", "JNJ", "LLY", "PFE"],
    "consumer": ["AMZN", "WMT", "COST", "MCD"],
    "crypto-adjacent": ["COIN", "MSTR", "MARA"],
    "indices": ["SPY", "QQQ", "DIA", "IWM"],
}


def available_themes() -> List[str]:
    return sorted(THEME_TICKERS.keys())


def expand_theme(theme: str) -> List[str]:
    return list(THEME_TICKERS.get(theme.strip().lower(), []))


def expand_interests(interests: Iterable[Dict[str, Any]]) -> List[str]:
    """Merge explicit tickers + theme expansions into a de-duped, ordered list.

    Each interest is a dict {kind: 'ticker'|'theme', value: str}.
    """
    out: List[str] = []
    seen: Set[str] = set()

    def add(sym: str) -> None:
        s = sym.strip().upper()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    for it in interests:
        kind = (it.get("kind") or "").lower()
        value = it.get("value") or ""
        if kind == "ticker":
            add(value)
        elif kind == "theme":
            for sym in expand_theme(value):
                add(sym)
    return out
