"""
Optional AI context notes via InvestorMate (https://pypi.org/project/investormate/).

All three conditions must be true for this module to produce output:
  1. config.yaml  ai_analysis.enabled: true
  2. OPENAI_API_KEY env var is set
  3. The `investormate` package is installed  (pip install investormate)

If any condition is unmet the function returns {} silently — the run continues
without AI notes. A failure on one ticker never aborts the others.

IMPORTANT framing: this tool is an ALERT tool, not a prediction tool. The
question sent to the model is wrapped with explicit guardrails so the note is
neutral qualitative *context* only — never a price forecast or buy/sell call.
"""
import os
from typing import Any, Dict, List

# Appended to every user question to keep output alert-appropriate.
# Signal-based assessment is allowed (an opinionated read grounded in the data),
# but it must remain decision-support — never a directive buy/sell/hold call.
_GUARDRAILS = (
    " Answer in 2-3 plain sentences. You may give a grounded qualitative "
    "assessment of the current technical/news picture and list factors a reader "
    "should weigh. Do NOT predict prices or future performance. Do NOT issue a "
    "directive buy, sell, or hold recommendation. Frame it as context to research "
    "further, not advice. Do not include any chart data."
)


def get_ai_notes(
    results: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Dict[str, str]:
    """Return a {ticker: note} dict, or {} if the feature is unavailable."""
    ai_cfg = config.get("ai_analysis", {})
    if not ai_cfg.get("enabled", False):
        return {}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {}

    try:
        from investormate import Investor
    except ImportError:
        return {}

    try:
        investor = Investor(openai_api_key=api_key, default_provider="openai")
    except Exception:
        return {}

    base_question: str = ai_cfg.get(
        "question",
        "What recent news themes or sector backdrop are most relevant to this stock right now?",
    )
    question = base_question + _GUARDRAILS

    notes: Dict[str, str] = {}
    for r in results:
        if r.get("error"):
            continue
        ticker = r["ticker"]
        try:
            # Investor.ask returns {"answer": str, "graph_data": ...}
            response = investor.ask(ticker, question)
            answer = (response or {}).get("answer")
            if answer:
                notes[ticker] = str(answer).strip()
        except Exception:
            # One bad ticker / API hiccup must never abort the rest
            continue

    return notes
