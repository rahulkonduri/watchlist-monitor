"""Deterministic, rules-based signal assessment.

This is the always-on, no-API decision-support layer. It turns a scan snapshot
(and optional portfolio position) into a neutral, indicator-grounded read.

IMPORTANT: This is decision-support, NOT financial advice. Output never contains
directive buy/sell/hold verbs — only an observation, the reasoning, and neutral
'factors to weigh'. The web layer must keep the not-advice framing visible.
"""
from typing import Any, Dict, List, Optional

# Tone labels are descriptive of the *technical condition*, not actions to take.
_LABEL_STRONG = "Technically strong"
_LABEL_WEAK = "Technically weak"
_LABEL_STRETCHED = "Looks stretched"
_LABEL_NEUTRAL = "Mixed / neutral"


def assess(
    result: Dict[str, Any],
    position: Optional[Dict[str, Any]] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return {label, rationale, factors[]} derived purely from indicators."""
    cfg = cfg or {}
    tcfg = cfg.get("triggers", {}) if isinstance(cfg, dict) else {}
    os_level = float(tcfg.get("rsi_oversold", 30))
    ob_level = float(tcfg.get("rsi_overbought", 70))

    if result.get("error"):
        return {
            "label": "No data",
            "rationale": f"Could not evaluate: {result['error']}",
            "factors": [],
        }

    rsi = result.get("rsi")
    cross = result.get("ma_cross")
    change = result.get("change_pct")

    reasons: List[str] = []
    factors: List[str] = []
    bull = 0
    bear = 0

    # RSI zone
    if rsi is not None:
        if rsi <= os_level:
            bear += 1
            reasons.append(f"RSI {rsi:.0f} is in oversold territory (<= {os_level:.0f})")
            factors.append("mean-reversion watchers sometimes look closer when RSI is low")
        elif rsi >= ob_level:
            bull += 1
            reasons.append(f"RSI {rsi:.0f} is in overbought territory (>= {ob_level:.0f})")
            factors.append("an extended RSI can stay extended; confirm with the trend")
        else:
            reasons.append(f"RSI {rsi:.0f} is in a neutral range")

    # Moving-average crossover
    if cross == "golden":
        bull += 1
        reasons.append("a golden cross (short SMA crossed above long SMA) just printed")
        factors.append("crossovers are lagging signals; they confirm trend rather than lead it")
    elif cross == "death":
        bear += 1
        reasons.append("a death cross (short SMA crossed below long SMA) just printed")
        factors.append("crossovers are lagging signals; they confirm trend rather than lead it")

    # Daily move magnitude
    if change is not None and abs(change) >= 3.0:
        direction = "up" if change > 0 else "down"
        reasons.append(f"a large daily move ({change:+.1f}%, {direction})")
        factors.append("check whether news or an earnings event drove the move")

    # Pick a label from the balance of bullish/bearish signals
    if bull and not bear:
        label = _LABEL_STRONG
    elif bear and not bull:
        label = _LABEL_WEAK
    elif bull and bear:
        label = _LABEL_STRETCHED
    else:
        label = _LABEL_NEUTRAL

    # Portfolio-aware context (still neutral — never an action)
    if position and position.get("unrealized_pl_pct") is not None:
        plp = position["unrealized_pl_pct"]
        sign = "up" if plp >= 0 else "down"
        reasons.append(f"your position is {sign} {abs(plp):.1f}% vs cost")
        factors.append("review against your own plan and risk tolerance, not this signal alone")

    rationale = ("; ".join(reasons) + ".") if reasons else "No notable technical signals today."
    # De-dupe factors while preserving order
    seen: set = set()
    factors = [f for f in factors if not (f in seen or seen.add(f))]

    return {"label": label, "rationale": rationale, "factors": factors}
