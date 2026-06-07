from typing import Any, Dict, Optional

import pandas as pd

from .indicators import daily_pct_change, ma_crossover, wilder_rsi


def evaluate(ticker: str, hist: Optional[pd.DataFrame], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate trigger conditions for a single ticker.

    Args:
        ticker: Ticker symbol string.
        hist:   DataFrame with at minimum a 'Close' column indexed by date.
        cfg:    Full config dict loaded from config.yaml.

    Returns:
        Dict with keys: ticker, price, change_pct, rsi, ma_cross, alerts, error.
        'alerts' is a list of human-readable strings for each fired trigger.
        'error' is None on success, otherwise an error description string.
    """
    result: Dict[str, Any] = {
        "ticker": ticker,
        "price": None,
        "change_pct": None,
        "rsi": None,
        "ma_cross": None,
        "alerts": [],
        "error": None,
    }

    try:
        if hist is None or hist.empty:
            result["error"] = "No data"
            return result

        closes = hist["Close"].dropna()
        if len(closes) < 2:
            result["error"] = "Insufficient data"
            return result

        tcfg = cfg.get("triggers", {})
        rsi_period = 14
        ma_short: int = int(tcfg.get("ma_short", 50))
        ma_long: int = int(tcfg.get("ma_long", 200))

        result["price"] = float(closes.iloc[-1])

        pct = daily_pct_change(closes)
        last_pct = pct.iloc[-1]
        result["change_pct"] = float(last_pct) if pd.notna(last_pct) else None

        rsi_series = wilder_rsi(closes, period=rsi_period)
        last_rsi = rsi_series.iloc[-1]
        result["rsi"] = float(last_rsi) if pd.notna(last_rsi) else None

        result["ma_cross"] = ma_crossover(closes, ma_short, ma_long)

        alerts = []

        threshold_move = tcfg.get("daily_move_pct")
        if threshold_move is not None and result["change_pct"] is not None:
            if abs(result["change_pct"]) >= float(threshold_move):
                direction = "up" if result["change_pct"] > 0 else "down"
                alerts.append(
                    f"Large daily move: {result['change_pct']:+.2f}% ({direction})"
                    f" >= {threshold_move}% threshold"
                )

        threshold_os = tcfg.get("rsi_oversold")
        if threshold_os is not None and result["rsi"] is not None:
            if result["rsi"] <= float(threshold_os):
                alerts.append(f"RSI oversold: {result['rsi']:.1f} <= {threshold_os}")

        threshold_ob = tcfg.get("rsi_overbought")
        if threshold_ob is not None and result["rsi"] is not None:
            if result["rsi"] >= float(threshold_ob):
                alerts.append(f"RSI overbought: {result['rsi']:.1f} >= {threshold_ob}")

        if result["ma_cross"] == "golden":
            alerts.append(
                f"Golden cross: {ma_short}-day SMA crossed above {ma_long}-day SMA"
            )
        elif result["ma_cross"] == "death":
            alerts.append(
                f"Death cross: {ma_short}-day SMA crossed below {ma_long}-day SMA"
            )

        result["alerts"] = alerts

    except Exception as exc:
        result["error"] = str(exc)

    return result
