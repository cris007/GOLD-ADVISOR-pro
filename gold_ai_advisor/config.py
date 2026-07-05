"""
Central configuration for the Gold AI Advisor.
All secrets are read from environment variables (use a .env file, never hardcode keys).
"""
import os
from dotenv import load_dotenv

load_dotenv()  # reads a .env file in the project root if present (local dev)


def _get_secret(key: str, default: str = "") -> str:
    """
    Reads a secret from Streamlit's secrets store when running on Streamlit
    Cloud (or locally via .streamlit/secrets.toml), falling back to a plain
    environment variable / .env for CLI use. Importing streamlit has no cost
    when it's not actually running as a Streamlit app.
    """
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


# --- Gemini ---
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY", "")
GEMINI_MODEL = _get_secret("GEMINI_MODEL", "gemini-2.5-flash")  # fast + cheap; bump to gemini-2.5-pro for deeper reasoning

# --- Market data tickers (Yahoo Finance symbols) ---
TICKERS = {
    "gold": "GC=F",       # COMEX Gold Futures (closest free proxy to XAUUSD; correlation is near 1.0)
    "dxy": "DX-Y.NYB",    # US Dollar Index — inversely correlated with gold
    "us10y": "^TNX",      # 10Y Treasury yield — real yields are gold's strongest macro driver
    "silver": "SI=F",     # used for a simple precious-metals confluence check
}

# --- Technical analysis parameters (mirrors the regime logic used in GreenCrowEA) ---
TA_PARAMS = {
    "ema_fast": 20,
    "ema_slow": 100,       # EMA(100) chosen over EMA(200) to reduce lag, per your Black Crow EA finding
    "rsi_period": 14,
    "rsi_overbought": 65,  # tightened from 70, consistent with your Black Crow EA sell-lag fix
    "rsi_oversold": 35,
    "adx_period": 14,
    "adx_trend_threshold": 22,  # below this = choppy/ranging regime
    "atr_period": 14,
}

# --- News sources (free RSS feeds, no API key required) ---
NEWS_FEEDS = [
    "https://www.kitco.com/rss/KitcoNews.xml",
    "https://www.fxstreet.com/rss/news",
    "https://www.investing.com/rss/news_285.rss",  # commodities news
    "https://www.forexlive.com/feed/news",
]
NEWS_KEYWORDS = [
    "gold", "xau", "bullion", "precious metal", "fed", "fomc", "rate cut",
    "rate hike", "inflation", "cpi", "dollar index", "dxy", "treasury yield",
    "safe haven", "geopolitical",
]
MAX_HEADLINES = 25

# --- Aggregator weights (must sum to 1.0) ---
SIGNAL_WEIGHTS = {
    "technical": 0.45,
    "fundamental": 0.30,
    "sentiment": 0.25,
}

# --- Cache ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
