"""Curated constituent lists for top US and India indexes.

Used by the market-wide screener so it can surface candidates beyond the user's
own watchlist. These are hand-curated snapshots — index membership changes over
time, and a stale/renamed ticker simply yields a graceful per-ticker error in
the scan (it never aborts the run). Indian symbols use Yahoo suffixes:
  .NS = NSE (NIFTY),  .BO = BSE (SENSEX).

This remains a present-tense screener: it flags CURRENT technical conditions.
It does not predict prices and issues no buy/sell recommendations.
"""
from typing import Any, Dict, List

# ── US: Dow Jones Industrial Average (30) ────────────────────────────────────
_DOW30 = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT",
]

# ── US: Nasdaq-100 (curated snapshot) ────────────────────────────────────────
_NASDAQ100 = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
    "PEP", "ADBE", "CSCO", "NFLX", "AMD", "TMUS", "INTC", "CMCSA", "QCOM", "INTU",
    "TXN", "AMGN", "HON", "AMAT", "ISRG", "BKNG", "VRTX", "ADP", "REGN", "GILD",
    "MU", "LRCX", "MDLZ", "PANW", "SBUX", "KLAC", "SNPS", "CDNS", "MAR", "CSX",
    "ORLY", "ASML", "ADI", "PYPL", "ABNB", "MRVL", "FTNT", "MNST", "CRWD", "WDAY",
    "DXCM", "NXPI", "MELI", "CTAS", "PCAR", "ROST", "ODFL", "PAYX", "KDP", "CHTR",
    "LULU", "IDXX", "FAST", "CPRT", "EXC", "VRSK", "EA", "BKR", "CCEP", "XEL",
    "CTSH", "DDOG", "GEHC", "KHC", "ON", "BIIB", "TTD", "ANSS", "CDW", "FANG",
    "DASH", "TEAM", "MRNA", "ZS", "WBD", "GFS", "ILMN", "MDB", "WBA", "ENPH",
]

# ── India: NIFTY 50 (NSE, .NS) ───────────────────────────────────────────────
_NIFTY50 = [s + ".NS" for s in [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT",
    "MARUTI", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND",
    "ONGC", "NTPC", "POWERGRID", "TATAMOTORS", "TATASTEEL", "ADANIENT", "ADANIPORTS",
    "COALINDIA", "JSWSTEEL", "GRASIM", "BAJAJFINSV", "HDFCLIFE", "SBILIFE",
    "BRITANNIA", "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO", "INDUSINDBK",
    "M&M", "TECHM", "APOLLOHOSP", "HINDALCO", "TATACONSUM", "BPCL", "LTIM",
    "DIVISLAB", "BAJAJ-AUTO", "SHRIRAMFIN",
]]

# ── India: BSE SENSEX (BSE, .BO) ─────────────────────────────────────────────
_SENSEX30 = [s + ".BO" for s in [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT",
    "MARUTI", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND",
    "NTPC", "POWERGRID", "TATAMOTORS", "TATASTEEL", "M&M", "INDUSINDBK", "TECHM",
    "BAJAJFINSV", "JSWSTEEL",
]]

INDEXES: Dict[str, Dict[str, Any]] = {
    "dow30": {"name": "Dow Jones 30 (US)", "currency": "USD", "symbol": "$", "country": "US", "tickers": _DOW30},
    "nasdaq100": {"name": "Nasdaq-100 (US)", "currency": "USD", "symbol": "$", "country": "US", "tickers": _NASDAQ100},
    "nifty50": {"name": "NIFTY 50 (India)", "currency": "INR", "symbol": "₹", "country": "IN", "tickers": _NIFTY50},
    "sensex30": {"name": "BSE SENSEX 30 (India)", "currency": "INR", "symbol": "₹", "country": "IN", "tickers": _SENSEX30},
}


def index_meta() -> List[Dict[str, Any]]:
    return [
        {"key": k, "name": v["name"], "currency": v["currency"], "symbol": v["symbol"],
         "country": v["country"], "count": len(v["tickers"])}
        for k, v in INDEXES.items()
    ]


def get_index(key: str) -> Dict[str, Any]:
    return INDEXES[key]
