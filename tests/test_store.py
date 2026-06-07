import importlib
import os

import pytest


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Fresh store backed by an isolated temp DB, with config-seed disabled."""
    db = tmp_path / "test.db"
    monkeypatch.setenv("WATCHLIST_DB", str(db))
    import monitor.store as store_mod

    importlib.reload(store_mod)
    # Point the seed source at a non-existent path so seeding is a no-op
    monkeypatch.setattr(store_mod, "_CONFIG_PATH", tmp_path / "nope.yaml")
    store_mod.init_db()
    return store_mod


class TestHoldings:
    def test_add_and_list(self, store):
        store.add_holding("aapl", 10, 100.0, "2025-01-01")
        rows = store.list_holdings()
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"  # upper-cased
        assert rows[0]["shares"] == 10

    def test_update(self, store):
        h = store.add_holding("X", 1, 1.0)
        store.update_holding(h["id"], shares=5)
        assert store.get_holding(h["id"])["shares"] == 5

    def test_delete(self, store):
        h = store.add_holding("X", 1, 1.0)
        assert store.delete_holding(h["id"]) is True
        assert store.list_holdings() == []


class TestInterests:
    def test_add_dedupes(self, store):
        store.add_interest("ticker", "nvda")
        store.add_interest("ticker", "NVDA")  # duplicate after normalize
        assert len(store.list_interests()) == 1

    def test_theme_lowercased(self, store):
        store.add_interest("theme", "AI")
        assert store.list_interests()[0]["value"] == "ai"


class TestSettingsAndCfg:
    def test_defaults_present(self, store):
        s = store.get_settings()
        assert s["triggers"]["rsi_oversold"] == 30
        assert s["ai_analysis"]["enabled"] is False

    def test_nested_merge(self, store):
        store.update_settings({"triggers": {"rsi_oversold": 25}})
        s = store.get_settings()
        assert s["triggers"]["rsi_oversold"] == 25
        assert s["triggers"]["rsi_overbought"] == 70  # untouched default preserved

    def test_build_cfg_merges_tickers(self, store):
        store.add_interest("ticker", "AAPL")
        store.add_interest("theme", "ai")  # expands to incl. MSFT, NVDA...
        store.add_holding("TSLA", 1, 1.0)
        cfg = store.build_cfg()
        assert "AAPL" in cfg["tickers"]
        assert "MSFT" in cfg["tickers"]
        assert "TSLA" in cfg["tickers"]  # holding folded in
        assert "triggers" in cfg and "ai_analysis" in cfg
