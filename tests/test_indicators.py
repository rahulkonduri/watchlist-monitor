import numpy as np
import pandas as pd
import pytest

from monitor.indicators import daily_pct_change, ma_crossover, sma, wilder_rsi


def series(*values):
    return pd.Series(list(values), dtype=float)


# ── SMA ───────────────────────────────────────────────────────────────────────

class TestSMA:
    def test_known_value(self):
        result = sma(series(1, 2, 3, 4, 5), period=3)
        assert result.iloc[-1] == pytest.approx(4.0)

    def test_first_period_minus_one_are_nan(self):
        result = sma(series(1, 2, 3, 4, 5), period=3)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert not pd.isna(result.iloc[2])

    def test_series_shorter_than_period_all_nan(self):
        assert sma(series(1, 2), period=5).isna().all()

    def test_period_1_equals_input(self):
        prices = series(10, 20, 30)
        pd.testing.assert_series_equal(sma(prices, period=1), prices, check_names=False)


# ── Wilder RSI ────────────────────────────────────────────────────────────────

class TestWilderRSI:
    def test_all_gains_gives_100(self):
        prices = series(*range(1, 20))  # monotonically increasing
        rsi = wilder_rsi(prices, period=14)
        assert rsi.dropna().iloc[-1] == pytest.approx(100.0)

    def test_all_losses_gives_0(self):
        prices = series(*range(20, 0, -1))  # monotonically decreasing
        rsi = wilder_rsi(prices, period=14)
        assert rsi.dropna().iloc[-1] == pytest.approx(0.0)

    def test_output_bounded_0_to_100(self):
        rng = np.random.default_rng(42)
        prices = pd.Series(np.cumsum(rng.standard_normal(120)) + 100)
        valid = wilder_rsi(prices, period=14).dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_first_period_values_are_nan(self):
        prices = series(*range(1, 20))  # 19 values, period 14
        rsi = wilder_rsi(prices, period=14)
        assert rsi.iloc[:14].isna().all()
        assert pd.notna(rsi.iloc[14])

    def test_insufficient_data_returns_all_nan(self):
        assert wilder_rsi(series(1.0, 2.0), period=14).isna().all()

    def test_flat_prices_give_nan(self):
        # flat series has no gains or losses — RSI is undefined
        prices = series(*([100.0] * 30))
        valid_rsi = wilder_rsi(prices, period=14).dropna()
        assert valid_rsi.isna().all() or len(valid_rsi) == 0


# ── Daily percent change ───────────────────────────────────────────────────────

class TestDailyPctChange:
    def test_10_pct_gain(self):
        assert daily_pct_change(series(100.0, 110.0)).iloc[-1] == pytest.approx(10.0)

    def test_10_pct_loss(self):
        assert daily_pct_change(series(100.0, 90.0)).iloc[-1] == pytest.approx(-10.0)

    def test_first_value_nan(self):
        assert pd.isna(daily_pct_change(series(100.0, 110.0)).iloc[0])

    def test_flat_gives_zero(self):
        assert daily_pct_change(series(50.0, 50.0)).iloc[-1] == pytest.approx(0.0)


# ── MA crossover ──────────────────────────────────────────────────────────────

class TestMACrossover:
    def _golden_prices(self):
        # prices fall to 1, then jump to 100 on the last bar —
        # SMA(2) was below SMA(4) at [-2], crosses above at [-1]
        return series(10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 100)

    def _death_prices(self):
        # prices rise to 10, then drop to 1 on the last bar —
        # SMA(2) was above SMA(4) at [-2], crosses below at [-1]
        return series(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 1)

    def test_golden_cross_detected(self):
        # At index 10: SMA2=1.0, SMA4=2.5 (short < long)
        # At index 11: SMA2=50.5, SMA4=26.5 (short > long) → golden
        assert ma_crossover(self._golden_prices(), short_period=2, long_period=4) == "golden"

    def test_death_cross_detected(self):
        # At index 10: SMA2=10.0, SMA4=9.25 (short > long)
        # At index 11: SMA2=5.5, SMA4=7.5 (short < long) → death
        assert ma_crossover(self._death_prices(), short_period=2, long_period=4) == "death"

    def test_no_cross_in_smooth_uptrend(self):
        # Smooth uptrend: short SMA always above long SMA, no crossover
        prices = series(*range(1, 21))
        assert ma_crossover(prices, short_period=3, long_period=5) is None

    def test_insufficient_data_returns_none(self):
        assert ma_crossover(series(1.0, 2.0, 3.0), short_period=5, long_period=10) is None

    def test_return_value_is_string_or_none(self):
        rng = np.random.default_rng(0)
        prices = pd.Series(np.cumsum(rng.standard_normal(60)) + 50)
        result = ma_crossover(prices, short_period=5, long_period=20)
        assert result in ("golden", "death", None)
