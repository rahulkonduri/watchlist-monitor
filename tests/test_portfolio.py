import pytest

from monitor.portfolio import compute_position, summarize


class TestComputePosition:
    def test_gain(self):
        h = {"id": 1, "ticker": "AAPL", "shares": 10, "cost_basis": 100.0}
        p = compute_position(h, 150.0)
        assert p["cost_total"] == 1000.0
        assert p["market_value"] == 1500.0
        assert p["unrealized_pl"] == 500.0
        assert p["unrealized_pl_pct"] == pytest.approx(50.0)

    def test_loss(self):
        h = {"id": 2, "ticker": "X", "shares": 5, "cost_basis": 200.0}
        p = compute_position(h, 100.0)
        assert p["unrealized_pl"] == -500.0
        assert p["unrealized_pl_pct"] == pytest.approx(-50.0)

    def test_no_price_returns_none_market(self):
        h = {"id": 3, "ticker": "X", "shares": 5, "cost_basis": 200.0}
        p = compute_position(h, None)
        assert p["cost_total"] == 1000.0
        assert p["market_value"] is None
        assert p["unrealized_pl"] is None
        assert p["unrealized_pl_pct"] is None

    def test_zero_cost_basis_no_pct_divzero(self):
        h = {"id": 4, "ticker": "X", "shares": 5, "cost_basis": 0.0}
        p = compute_position(h, 10.0)
        assert p["unrealized_pl"] == 50.0
        assert p["unrealized_pl_pct"] is None


class TestSummarize:
    def test_totals(self):
        positions = [
            compute_position({"shares": 10, "cost_basis": 100.0}, 150.0),
            compute_position({"shares": 5, "cost_basis": 200.0}, 100.0),
        ]
        s = summarize(positions)
        assert s["total_cost"] == 2000.0
        assert s["total_value"] == 2000.0
        assert s["total_pl"] == 0.0
        assert s["total_pl_pct"] == pytest.approx(0.0)

    def test_all_missing_price(self):
        positions = [compute_position({"shares": 10, "cost_basis": 100.0}, None)]
        s = summarize(positions)
        assert s["total_value"] is None
        assert s["total_pl"] is None
