from monitor.assessment import assess

CFG = {"triggers": {"rsi_oversold": 30, "rsi_overbought": 70}}

_DIRECTIVE_WORDS = ["buy", "sell", "hold ", "should buy", "should sell"]


def _snap(**kw):
    base = {"ticker": "X", "price": 100.0, "change_pct": 0.0, "rsi": 50.0, "ma_cross": None, "alerts": [], "error": None}
    base.update(kw)
    return base


class TestAssess:
    def test_oversold_is_weak(self):
        a = assess(_snap(rsi=25.0), cfg=CFG)
        assert a["label"] == "Technically weak"
        assert "oversold" in a["rationale"].lower()

    def test_golden_cross_strong(self):
        a = assess(_snap(rsi=55.0, ma_cross="golden"), cfg=CFG)
        assert a["label"] == "Technically strong"

    def test_conflicting_signals_stretched(self):
        # overbought (bull) + death cross (bear)
        a = assess(_snap(rsi=80.0, ma_cross="death"), cfg=CFG)
        assert a["label"] == "Looks stretched"

    def test_neutral(self):
        a = assess(_snap(rsi=50.0), cfg=CFG)
        assert a["label"] == "Mixed / neutral"

    def test_error_snapshot(self):
        a = assess({"ticker": "X", "error": "No data"}, cfg=CFG)
        assert a["label"] == "No data"

    def test_position_context_included(self):
        a = assess(_snap(rsi=25.0), position={"unrealized_pl_pct": -12.3}, cfg=CFG)
        assert "12.3%" in a["rationale"]

    def test_never_directive_language(self):
        # Exercise several conditions; none should contain buy/sell/hold directives
        for snap in [
            _snap(rsi=20.0, ma_cross="death", change_pct=-5.0),
            _snap(rsi=85.0, ma_cross="golden", change_pct=6.0),
            _snap(rsi=50.0),
        ]:
            a = assess(snap, cfg=CFG)
            blob = (a["label"] + " " + a["rationale"] + " " + " ".join(a["factors"])).lower()
            for word in _DIRECTIVE_WORDS:
                assert word not in blob, f"directive word '{word}' leaked: {blob}"
