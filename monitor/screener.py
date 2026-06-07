"""Daily Ideas screener.

Surfaces and ranks tickers from the user's own universe (watchlist + themes +
holdings) by transparent, current technical conditions. Pure + unit-testable.

IMPORTANT: This is a SCREENER, not a recommendation engine. It groups
'research candidates' by the signal that flagged them. It never tells the user
to buy, sell, or hold — there are no directive ratings here. The web/UI layer
must keep the 'candidates to research, not advice' framing visible.
"""
from typing import Any, Dict, List, Optional

from .assessment import assess

# Group metadata: key -> (title, neutral blurb)
_GROUPS = [
    ("oversold", "Oversold by RSI", "Trading at a low RSI — some mean-reversion watchers look closer here."),
    ("overbought", "Overbought by RSI", "Trading at a high RSI — momentum can persist, so confirm with the trend."),
    ("golden", "Golden cross (uptrend signal)", "Short SMA just crossed above the long SMA on the latest bar."),
    ("death", "Death cross (downtrend signal)", "Short SMA just crossed below the long SMA on the latest bar."),
    ("movers", "Big daily movers", "Moved more than your daily-move threshold today."),
]


def _item(result: Dict[str, Any], cfg: Dict[str, Any], reasons: List[str], ai_notes: Dict[str, str]) -> Dict[str, Any]:
    return {
        "ticker": result["ticker"],
        "price": result.get("price"),
        "change_pct": result.get("change_pct"),
        "rsi": result.get("rsi"),
        "ma_cross": result.get("ma_cross"),
        "reasons": reasons,
        "assessment": assess(result, cfg=cfg),
        "ai_note": ai_notes.get(result["ticker"]),
    }


def build_ideas(
    results: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    ai_notes: Optional[Dict[str, str]] = None,
    top_n: int = 5,
    group_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Return categorized 'ideas' + a ranked 'top candidates' list.

    Ranking is a transparent score = number of distinct signals that fired,
    tie-broken by the size of the daily move. No buy/sell scoring.

    group_limit caps how many items each signal group returns (useful for the
    large market-wide scans so the UI stays readable).
    """
    ai_notes = ai_notes or {}
    tcfg = cfg.get("triggers", {}) if isinstance(cfg, dict) else {}
    os_level = float(tcfg.get("rsi_oversold", 30))
    ob_level = float(tcfg.get("rsi_overbought", 70))
    move = float(tcfg.get("daily_move_pct", 3.0))

    valid = [r for r in results if not r.get("error") and r.get("price") is not None]

    # Collect the per-ticker reasons that fired, keyed by group.
    grouped: Dict[str, List[Dict[str, Any]]] = {k: [] for k, _, _ in _GROUPS}
    reasons_by_ticker: Dict[str, List[str]] = {}

    def add_reason(ticker: str, text: str) -> None:
        reasons_by_ticker.setdefault(ticker, []).append(text)

    for r in valid:
        rsi = r.get("rsi")
        cross = r.get("ma_cross")
        chg = r.get("change_pct")

        if rsi is not None and rsi <= os_level:
            add_reason(r["ticker"], f"RSI {rsi:.0f} (oversold, <= {os_level:.0f})")
            grouped["oversold"].append(r)
        if rsi is not None and rsi >= ob_level:
            add_reason(r["ticker"], f"RSI {rsi:.0f} (overbought, >= {ob_level:.0f})")
            grouped["overbought"].append(r)
        if cross == "golden":
            add_reason(r["ticker"], "golden cross on the latest bar")
            grouped["golden"].append(r)
        if cross == "death":
            add_reason(r["ticker"], "death cross on the latest bar")
            grouped["death"].append(r)
        if chg is not None and abs(chg) >= move:
            add_reason(r["ticker"], f"moved {chg:+.1f}% today (>= {move:.1f}%)")
            grouped["movers"].append(r)

    # Sort each group sensibly
    grouped["oversold"].sort(key=lambda r: r["rsi"])
    grouped["overbought"].sort(key=lambda r: -r["rsi"])
    grouped["movers"].sort(key=lambda r: -abs(r["change_pct"]))

    groups_out = []
    for key, title, blurb in _GROUPS:
        chosen = grouped[key][:group_limit] if group_limit else grouped[key]
        items = [_item(r, cfg, reasons_by_ticker.get(r["ticker"], []), ai_notes) for r in chosen]
        groups_out.append(
            {"key": key, "title": title, "blurb": blurb, "items": items, "total": len(grouped[key])}
        )

    # Ranked top candidates: by signal count, then daily-move magnitude
    flagged = {r["ticker"]: r for r in valid if reasons_by_ticker.get(r["ticker"])}
    ranked = sorted(
        flagged.values(),
        key=lambda r: (len(reasons_by_ticker[r["ticker"]]), abs(r.get("change_pct") or 0.0)),
        reverse=True,
    )
    top = [_item(r, cfg, reasons_by_ticker[r["ticker"]], ai_notes) for r in ranked[:top_n]]

    return {
        "top": top,
        "groups": groups_out,
        "counts": {
            "universe": len(results),
            "flagged": len(flagged),
        },
    }
