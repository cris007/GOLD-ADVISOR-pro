"""
Technical analysis layer.
Computes EMA, RSI, ADX, ATR from raw OHLC data and converts them into
a single directional score in [-1, +1], mirroring the regime-based logic
philosophy used in GreenCrowEA (ADX filters chop, EMA defines trend bias,
ATR sizes conviction/volatility context).
"""
import numpy as np
import pandas as pd
from config import TA_PARAMS


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[(plus_dm < 0) | (plus_dm < minus_dm)] = 0
    minus_dm[(minus_dm < 0) | (minus_dm < plus_dm)] = 0

    tr = atr(df, 1) * 1  # true range (unsmoothed)
    atr_smooth = tr.rolling(period).mean().replace(0, np.nan)

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_smooth)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_smooth)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.rolling(period).mean()


def analyze(df: pd.DataFrame) -> dict:
    """
    Returns a dict with raw indicator values plus a composite technical score
    in [-1, +1] (negative = bearish, positive = bullish) and a regime label.
    """
    if df is None or len(df) < max(TA_PARAMS["ema_slow"], TA_PARAMS["adx_period"]) + 5:
        return {"error": "insufficient data for technical analysis"}

    close = df["Close"]
    ema_fast = ema(close, TA_PARAMS["ema_fast"]).iloc[-1]
    ema_slow = ema(close, TA_PARAMS["ema_slow"]).iloc[-1]
    rsi_val = rsi(close, TA_PARAMS["rsi_period"]).iloc[-1]
    adx_val = adx(df, TA_PARAMS["adx_period"]).iloc[-1]
    atr_val = atr(df, TA_PARAMS["atr_period"]).iloc[-1]
    price = close.iloc[-1]

    regime = "trending" if adx_val >= TA_PARAMS["adx_trend_threshold"] else "choppy"

    # --- Trend component: price vs EMA stack ---
    trend_score = 0.0
    if price > ema_fast > ema_slow:
        trend_score = 1.0
    elif price < ema_fast < ema_slow:
        trend_score = -1.0
    elif price > ema_slow:
        trend_score = 0.4
    elif price < ema_slow:
        trend_score = -0.4

    # --- Momentum component: RSI ---
    momentum_score = 0.0
    if rsi_val >= TA_PARAMS["rsi_overbought"]:
        momentum_score = -0.5  # overbought -> pullback risk
    elif rsi_val <= TA_PARAMS["rsi_oversold"]:
        momentum_score = 0.5   # oversold -> bounce risk
    else:
        momentum_score = (rsi_val - 50) / 50 * 0.5  # mild continuation bias

    # In choppy regime, discount trend score (this mirrors GreenCrowEA's ADX regime filter)
    regime_multiplier = 1.0 if regime == "trending" else 0.4
    composite = (trend_score * 0.7 + momentum_score * 0.3) * regime_multiplier
    composite = max(-1.0, min(1.0, composite))

    return {
        "price": round(float(price), 2),
        "ema_fast": round(float(ema_fast), 2),
        "ema_slow": round(float(ema_slow), 2),
        "rsi": round(float(rsi_val), 1),
        "adx": round(float(adx_val), 1),
        "atr": round(float(atr_val), 2),
        "regime": regime,
        "score": round(float(composite), 3),
    }
