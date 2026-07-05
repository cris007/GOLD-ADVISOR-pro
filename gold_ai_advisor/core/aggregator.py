"""
Combines the technical, fundamental, and sentiment scores into a single
weighted verdict: BUY / SELL / WAIT plus a confidence percentage.
This mirrors the confluence approach used in your Bullion Desk dashboard,
just implemented in Python instead of React.
"""
from config import SIGNAL_WEIGHTS


def build_verdict(technical: dict, fundamental: dict, sentiment: dict) -> dict:
    tech_score = technical.get("score", 0.0) if "error" not in technical else 0.0
    fund_score = fundamental.get("score", 0.0) if "error" not in fundamental else 0.0
    sent_score = sentiment.get("score", 0.0)

    weighted = (
        tech_score * SIGNAL_WEIGHTS["technical"]
        + fund_score * SIGNAL_WEIGHTS["fundamental"]
        + sent_score * SIGNAL_WEIGHTS["sentiment"]
    )

    # Confidence = how strongly the signals agree AND how large the composite is
    scores = [tech_score, fund_score, sent_score]
    signs = [1 if s > 0.05 else (-1 if s < -0.05 else 0) for s in scores]
    agreement = signs.count(max(set(signs), key=signs.count)) / len(signs) if signs else 0
    magnitude = min(1.0, abs(weighted) * 1.5)
    confidence = round((0.5 * agreement + 0.5 * magnitude) * 100, 1)

    if weighted > 0.15:
        verdict = "BUY"
    elif weighted < -0.15:
        verdict = "SELL"
    else:
        verdict = "WAIT"

    # Choppy regime override: even a decent score shouldn't be traded with full conviction
    if technical.get("regime") == "choppy" and verdict != "WAIT":
        confidence = round(confidence * 0.6, 1)

    return {
        "verdict": verdict,
        "confidence_pct": confidence,
        "composite_score": round(weighted, 3),
        "components": {
            "technical": tech_score,
            "fundamental": fund_score,
            "sentiment": sent_score,
        },
    }
