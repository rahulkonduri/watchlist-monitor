"""Pure portfolio P&L math. No I/O, fully unit-testable.

A 'holding' is a dict: {id, ticker, shares, cost_basis, purchased_on}
where cost_basis is the per-share purchase price.
"""
from typing import Any, Dict, List, Optional


def compute_position(holding: Dict[str, Any], current_price: Optional[float]) -> Dict[str, Any]:
    """Return market value, cost, and unrealized P&L for a single holding.

    If current_price is unavailable (None), market-value fields are None.
    """
    shares = float(holding.get("shares") or 0.0)
    cost_per_share = float(holding.get("cost_basis") or 0.0)
    cost_total = shares * cost_per_share

    pos: Dict[str, Any] = {
        "id": holding.get("id"),
        "ticker": holding.get("ticker"),
        "shares": shares,
        "cost_basis": cost_per_share,
        "cost_total": round(cost_total, 2),
        "current_price": None,
        "market_value": None,
        "unrealized_pl": None,
        "unrealized_pl_pct": None,
    }

    if current_price is None:
        return pos

    current_price = float(current_price)
    market_value = shares * current_price
    unrealized_pl = market_value - cost_total

    pos["current_price"] = round(current_price, 2)
    pos["market_value"] = round(market_value, 2)
    pos["unrealized_pl"] = round(unrealized_pl, 2)
    pos["unrealized_pl_pct"] = (
        round((unrealized_pl / cost_total) * 100.0, 2) if cost_total > 0 else None
    )
    return pos


def summarize(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate totals across positions, ignoring those with no market value."""
    total_cost = 0.0
    total_value = 0.0
    have_value = False

    for p in positions:
        total_cost += float(p.get("cost_total") or 0.0)
        if p.get("market_value") is not None:
            total_value += float(p["market_value"])
            have_value = True

    if not have_value:
        return {
            "total_cost": round(total_cost, 2),
            "total_value": None,
            "total_pl": None,
            "total_pl_pct": None,
        }

    total_pl = total_value - total_cost
    return {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_pl": round(total_pl, 2),
        "total_pl_pct": round((total_pl / total_cost) * 100.0, 2) if total_cost > 0 else None,
    }
