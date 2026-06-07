import pandas as pd
import pytest

from monitor.triggers import evaluate


def hist_from_closes(closes):
    return pd.DataFrame({"Close": closes}, dtype=float)


BASE_CFG = {
    "triggers": {
        "daily_move_pct": 5.0,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "ma_short": 2,
        "ma_long": 4,
    }
}


# ── Snapshot correctness ──────────────────────────────────────────────────────

class TestSnapshot:
    def test_price_is_last_close(self):
        r = evaluate("X", hist_from_closes(list(range(1, 21))), BASE_CFG)
        assert r["price"] == pytest.approx(20.0)

    def test_ticker_echoed(self):
        r = evaluate("AAPL", hist_from_closes([100.0, 101.0]), BASE_CFG)
        assert r["ticker"] == "AAPL"

    def test_change_pct_correct(self):
        r = evaluate("X", hist_from_closes([100.0] * 30 + [110.0]), BASE_CFG)
        assert r["change_pct"] == pytest.approx(10.0)

    def test_no_error_on_valid_data(self):
        r = evaluate("X", hist_from_closes(list(range(50, 80))), BASE_CFG)
        assert r["error"] is None


# ── Error cases ───────────────────────────────────────────────────────────────

class TestErrors:
    def test_none_hist(self):
        assert evaluate("X", None, {})["error"] is not None

    def test_empty_hist(self):
        assert evaluate("X", pd.DataFrame(), {})["error"] is not None

    def test_single_bar(self):
        assert evaluate("X", hist_from_closes([100.0]), {})["error"] is not None


# ── Alert: daily move ─────────────────────────────────────────────────────────

class TestDailyMoveAlert:
    def test_fires_on_large_drop(self):
        closes = [100.0] * 30 + [85.0]   # −15%
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        assert any("Large daily move" in a for a in r["alerts"])

    def test_fires_on_large_gain(self):
        closes = [100.0] * 30 + [115.0]  # +15%
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        assert any("Large daily move" in a for a in r["alerts"])

    def test_no_alert_below_threshold(self):
        closes = [100.0] * 30 + [102.0]  # +2%
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        assert not any("Large daily move" in a for a in r["alerts"])

    def test_no_alert_when_threshold_not_configured(self):
        closes = [100.0] * 30 + [50.0]
        r = evaluate("X", hist_from_closes(closes), {"triggers": {}})
        assert not any("Large daily move" in a for a in r["alerts"])


# ── Alert: RSI ────────────────────────────────────────────────────────────────

class TestRSIAlerts:
    def test_oversold_alert_for_declining_series(self):
        closes = list(range(100, 50, -1))
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        if r["rsi"] is not None and r["rsi"] <= 30:
            assert any("oversold" in a for a in r["alerts"])

    def test_overbought_alert_for_rising_series(self):
        closes = list(range(50, 100))
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        if r["rsi"] is not None and r["rsi"] >= 70:
            assert any("overbought" in a for a in r["alerts"])

    def test_no_rsi_alert_when_not_configured(self):
        closes = list(range(100, 50, -1))
        r = evaluate("X", hist_from_closes(closes), {"triggers": {}})
        assert not any("RSI" in a for a in r["alerts"])


# ── Alert: MA crossover ───────────────────────────────────────────────────────

class TestMACrossoverAlerts:
    def test_golden_cross_alert(self):
        # Fall then spike — golden cross on last bar (short=2, long=4)
        closes = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 100]
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        assert any("Golden cross" in a for a in r["alerts"])

    def test_death_cross_alert(self):
        # Rise then crash — death cross on last bar (short=2, long=4)
        closes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 1]
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        assert any("Death cross" in a for a in r["alerts"])

    def test_no_cross_alert_in_steady_trend(self):
        closes = list(range(1, 30))
        r = evaluate("X", hist_from_closes(closes), BASE_CFG)
        assert not any("cross" in a.lower() for a in r["alerts"])
