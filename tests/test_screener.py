from monitor.screener import build_ideas

CFG = {"triggers": {"rsi_oversold": 30, "rsi_overbought": 70, "daily_move_pct": 3.0, "ma_short": 50, "ma_long": 200}}

_DIRECTIVE = ["buy", "sell", " hold", "strong buy", "price target"]


def snap(ticker, **kw):
    base = {"ticker": ticker, "price": 100.0, "change_pct": 0.0, "rsi": 50.0, "ma_cross": None, "alerts": [], "error": None}
    base.update(kw)
    return base


def test_oversold_grouped():
    results = [snap("A", rsi=20.0), snap("B", rsi=55.0)]
    data = build_ideas(results, CFG)
    grp = {g["key"]: g for g in data["groups"]}
    tickers = [i["ticker"] for i in grp["oversold"]["items"]]
    assert tickers == ["A"]


def test_movers_sorted_by_magnitude():
    results = [snap("A", change_pct=4.0), snap("B", change_pct=-9.0), snap("C", change_pct=1.0)]
    grp = {g["key"]: g for g in build_ideas(results, CFG)["groups"]}
    movers = [i["ticker"] for i in grp["movers"]["items"]]
    assert movers == ["B", "A"]  # C below threshold; B bigger magnitude first


def test_crosses_grouped():
    results = [snap("G", ma_cross="golden"), snap("D", ma_cross="death")]
    grp = {g["key"]: g for g in build_ideas(results, CFG)["groups"]}
    assert grp["golden"]["items"][0]["ticker"] == "G"
    assert grp["death"]["items"][0]["ticker"] == "D"


def test_top_ranked_by_signal_count():
    # A fires 2 signals (oversold + big move); B fires 1
    results = [snap("A", rsi=20.0, change_pct=-8.0), snap("B", rsi=25.0)]
    top = build_ideas(results, CFG)["top"]
    assert top[0]["ticker"] == "A"
    assert len(top[0]["reasons"]) >= 2


def test_errors_and_unflagged_excluded():
    results = [snap("OK", rsi=50.0), {"ticker": "ERR", "error": "boom"}]
    data = build_ideas(results, CFG)
    assert data["counts"]["universe"] == 2
    assert data["counts"]["flagged"] == 0
    assert data["top"] == []


def test_never_directive_language():
    results = [snap("A", rsi=15.0, ma_cross="death", change_pct=-7.0), snap("B", rsi=85.0, ma_cross="golden", change_pct=6.0)]
    data = build_ideas(results, CFG)
    blobs = []
    for it in data["top"]:
        a = it["assessment"]
        blobs.append((" ".join(it["reasons"]) + a["label"] + a["rationale"] + " ".join(a["factors"])).lower())
    for g in data["groups"]:
        blobs.append((g["title"] + g["blurb"]).lower())
    for blob in blobs:
        for word in _DIRECTIVE:
            assert word not in blob, f"directive '{word}' leaked: {blob}"
