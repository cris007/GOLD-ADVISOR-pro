"""
Fetches OHLC price history for gold and its key macro correlates.
Uses yfinance (free, no API key). Falls back gracefully with clear errors
if Yahoo Finance is unreachable or a ticker has no data.
"""
import pandas as pd
import yfinance as yf
from config import TICKERS


def fetch_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV history for a single ticker. Returns an empty DataFrame on failure."""
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df is None or df.empty:
            print(f"[market_data] Warning: no data returned for {ticker}")
            return pd.DataFrame()
        df.index.name = "date"
        return df
    except Exception as e:
        print(f"[market_data] Error fetching {ticker}: {e}")
        return pd.DataFrame()


def fetch_all(period: str = "6mo", interval: str = "1d") -> dict:
    """Fetch gold + DXY + 10Y yield + silver in one call. Returns {name: DataFrame}."""
    return {name: fetch_history(symbol, period, interval) for name, symbol in TICKERS.items()}


def latest_price(df: pd.DataFrame) -> float | None:
    if df is None or df.empty:
        return None
    return float(df["Close"].iloc[-1])


def pct_change(df: pd.DataFrame, lookback: int = 5) -> float | None:
    """Percent change over the last `lookback` bars."""
    if df is None or len(df) <= lookback:
        return None
    recent = df["Close"].iloc[-1]
    past = df["Close"].iloc[-1 - lookback]
    if past == 0:
        return None
    return float((recent - past) / past * 100)


if __name__ == "__main__":
    data = fetch_all(period="1mo")
    for name, df in data.items():
        print(name, "->", latest_price(df), f"({pct_change(df):.2f}% / 5 bars)" if not df.empty else "no data")
