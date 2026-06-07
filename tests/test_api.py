import importlib

import pandas as pd
import pytest
from fastapi.testclient import TestClient


def _synthetic_hist(ticker):
    # 60 rising closes -> deterministic, offline; price = last close
    closes = [float(50 + i) for i in range(60)]
    return pd.DataFrame({"Close": closes})


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DB", str(tmp_path / "api.db"))

    import monitor.store as store_mod
    import monitor.core as core_mod

    importlib.reload(store_mod)
    importlib.reload(core_mod)
    # No network: stub the fetches the scan() / market-scan paths use
    monkeypatch.setattr(core_mod, "fetch_history", lambda t, use_cache=True: _synthetic_hist(t))
    monkeypatch.setattr(core_mod, "fetch_many", lambda tickers, refresh=False: {t: _synthetic_hist(t) for t in tickers})
    monkeypatch.setattr(store_mod, "_CONFIG_PATH", tmp_path / "nope.yaml")

    import webapp.main as main_mod
    importlib.reload(main_mod)
    # Disable scheduler in tests
    main_mod._scheduler = None

    with TestClient(main_mod.app) as c:
        yield c


class TestInterestsApi:
    def test_add_and_list(self, client):
        r = client.post("/api/interests", json={"kind": "ticker", "value": "aapl"})
        assert r.status_code == 200
        data = client.get("/api/interests").json()
        assert any(i["value"] == "AAPL" for i in data["interests"])
        assert "ai" in data["available_themes"]

    def test_bad_kind_rejected(self, client):
        assert client.post("/api/interests", json={"kind": "bogus", "value": "x"}).status_code == 400


class TestHoldingsApi:
    def test_crud(self, client):
        created = client.post("/api/holdings", json={"ticker": "AAPL", "shares": 10, "cost_basis": 50.0}).json()
        hid = created["id"]
        assert client.get("/api/holdings").json()[0]["ticker"] == "AAPL"
        client.put(f"/api/holdings/{hid}", json={"shares": 20})
        assert client.get("/api/holdings").json()[0]["shares"] == 20
        assert client.delete(f"/api/holdings/{hid}").status_code == 200
        assert client.get("/api/holdings").json() == []


class TestPortfolioApi:
    def test_pnl_computed(self, client):
        # synthetic last close = 50 + 59 = 109
        client.post("/api/holdings", json={"ticker": "AAPL", "shares": 10, "cost_basis": 100.0})
        data = client.get("/api/portfolio").json()
        pos = data["positions"][0]
        assert pos["current_price"] == 109.0
        assert pos["market_value"] == 1090.0
        assert pos["unrealized_pl"] == 90.0
        assert data["summary"]["total_pl"] == 90.0


class TestDashboardApi:
    def test_dashboard_has_assessment(self, client):
        client.post("/api/interests", json={"kind": "ticker", "value": "AAPL"})
        data = client.get("/api/dashboard").json()
        assert data["counts"]["tickers"] == 1
        row = data["rows"][0]
        assert row["ticker"] == "AAPL"
        assert "assessment" in row and "label" in row["assessment"]

    def test_dashboard_no_directive_language(self, client):
        client.post("/api/interests", json={"kind": "theme", "value": "ai"})
        data = client.get("/api/dashboard").json()
        for row in data["rows"]:
            a = row["assessment"]
            blob = (a["label"] + a["rationale"] + " ".join(a["factors"])).lower()
            for w in ["buy", "sell", " hold"]:
                assert w not in blob


class TestMarketScanApi:
    def test_universe_lists_indexes(self, client):
        data = client.get("/api/universe").json()
        keys = {i["key"] for i in data["indexes"]}
        assert {"dow30", "nifty50"}.issubset(keys)

    def test_market_scan_returns_ideas(self, client):
        data = client.get("/api/market-scan?index=dow30").json()
        assert data["index"]["key"] == "dow30"
        assert data["index"]["symbol"] == "$"
        assert data["counts"]["universe"] == 30
        assert "top" in data and "groups" in data

    def test_market_scan_india_currency(self, client):
        data = client.get("/api/market-scan?index=nifty50").json()
        assert data["index"]["symbol"] == "₹"

    def test_unknown_index_404(self, client):
        assert client.get("/api/market-scan?index=bogus").status_code == 404

    def test_market_scan_no_directive_language(self, client):
        data = client.get("/api/market-scan?index=dow30").json()
        for it in data["top"]:
            a = it["assessment"]
            blob = (" ".join(it["reasons"]) + a["label"] + a["rationale"] + " ".join(a["factors"])).lower()
            for w in ["buy", "sell", " hold", "price target", "will rise", "will fall"]:
                assert w not in blob


class TestSettingsApi:
    def test_get_and_update(self, client):
        client.put("/api/settings", json={"triggers": {"rsi_oversold": 25}})
        s = client.get("/api/settings").json()
        assert s["triggers"]["rsi_oversold"] == 25
        assert "_env" in s  # env status surfaced for the UI
