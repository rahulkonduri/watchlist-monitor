from monitor.universe import INDEXES, get_index, index_meta


def test_expected_indexes_present():
    for key in ("dow30", "nasdaq100", "nifty50", "sensex30"):
        assert key in INDEXES


def test_india_suffixes():
    assert all(t.endswith(".NS") for t in INDEXES["nifty50"]["tickers"])
    assert all(t.endswith(".BO") for t in INDEXES["sensex30"]["tickers"])


def test_us_have_no_suffix():
    assert all("." not in t for t in INDEXES["dow30"]["tickers"])


def test_currency_symbols():
    assert INDEXES["dow30"]["symbol"] == "$"
    assert INDEXES["nifty50"]["symbol"] == "₹"


def test_index_meta_counts_match():
    meta = {m["key"]: m for m in index_meta()}
    assert meta["dow30"]["count"] == len(INDEXES["dow30"]["tickers"])
    assert meta["nifty50"]["country"] == "IN"


def test_get_index_keyerror():
    import pytest

    with pytest.raises(KeyError):
        get_index("nope")
