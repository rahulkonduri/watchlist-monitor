from monitor.themes import available_themes, expand_interests, expand_theme


def test_available_themes_nonempty():
    assert "ai" in available_themes()


def test_expand_theme_known():
    assert "NVDA" in expand_theme("ai")
    assert expand_theme("AI") == expand_theme("ai")  # case-insensitive


def test_expand_theme_unknown_empty():
    assert expand_theme("not-a-theme") == []


def test_expand_interests_dedupes_and_merges():
    interests = [
        {"kind": "ticker", "value": "aapl"},
        {"kind": "theme", "value": "ai"},      # includes MSFT, GOOGL, NVDA...
        {"kind": "ticker", "value": "NVDA"},   # already from theme -> deduped
    ]
    out = expand_interests(interests)
    assert out[0] == "AAPL"           # explicit ticker first, upper-cased
    assert out.count("NVDA") == 1     # de-duped
    assert "MSFT" in out              # theme expansion present
