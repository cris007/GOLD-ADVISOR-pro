"""
Fundamental driver layer.
Gold has two dominant, well-documented macro drivers that are cheap to track
programmatically without a paid data feed:
  1. USD strength (DXY) - inverse correlation with gold
  2. US Treasury yields (^TNX proxy for real rates) - inverse correlation with gold
Silver is included as a simple precious-metals confluence check (if silver
disagrees sharply with gold's move, treat the fundamental read with less confidence).
"""
from core.market_data import pct_change, latest_price


def analyze(data: dict) -> dict:
    """
    `data` is the dict returned by market_data.fetch_all(): {"gold": df, "dxy": df, "us10y": df, "silver": df}
    Returns a fundamental score in [-1, +1] plus the underlying reads.
    """
    dxy_chg = pct_change(data.get("dxy"), lookback=10)
    yield_chg = pct_change(data.get("us10y"), lookback=10)
    silver_chg = pct_change(data.get("silver"), lookback=10)
    gold_chg = pct_change(data.get("gold"), lookback=10)

    if dxy_chg is None and yield_chg is None:
        return {"error": "insufficient macro data"}

    score = 0.0
    notes = []

    if dxy_chg is not None:
        # DXY rising -> bearish gold; DXY falling -> bullish gold
        dxy_component = max(-1.0, min(1.0, -dxy_chg / 2.0))
        score += dxy_component * 0.55
        notes.append(f"DXY {'up' if dxy_chg > 0 else 'down'} {abs(dxy_chg):.2f}% (10 bars) -> {'bearish' if dxy_chg > 0 else 'bullish'} gold")

    if yield_chg is not None:
        # Rising yields -> bearish gold (higher opportunity cost); falling yields -> bullish gold
        yield_component = max(-1.0, min(1.0, -yield_chg / 3.0))
        score += yield_component * 0.45
        notes.append(f"10Y yield {'up' if yield_chg > 0 else 'down'} {abs(yield_chg):.2f}% (10 bars) -> {'bearish' if yield_chg > 0 else 'bullish'} gold")

    confluence = "aligned"
    if silver_chg is not None and gold_chg is not None:
        if (silver_chg > 0) != (gold_chg > 0) and abs(silver_chg - gold_chg) > 2:
            confluence = "diverging"
            notes.append(f"Silver diverging from gold (silver {silver_chg:+.2f}% vs gold {gold_chg:+.2f}%) -> lower confidence")

    score = max(-1.0, min(1.0, score))

    return {
        "dxy_change_pct": round(dxy_chg, 2) if dxy_chg is not None else None,
        "us10y_change_pct": round(yield_chg, 2) if yield_chg is not None else None,
        "silver_confluence": confluence,
        "score": round(score, 3),
        "notes": notes,
    }
