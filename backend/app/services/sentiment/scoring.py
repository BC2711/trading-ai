from __future__ import annotations


POSITIVE_TERMS = {
    "accumulation": 0.18,
    "adoption": 0.22,
    "approval": 0.24,
    "breakout": 0.28,
    "bullish": 0.3,
    "demand": 0.18,
    "growth": 0.16,
    "inflows": 0.22,
    "institutional": 0.16,
    "partnership": 0.18,
    "rally": 0.24,
    "support": 0.12,
    "upgrade": 0.2,
}

NEGATIVE_TERMS = {
    "bearish": -0.3,
    "crackdown": -0.28,
    "decline": -0.18,
    "exploit": -0.35,
    "hack": -0.34,
    "lawsuit": -0.24,
    "liquidations": -0.25,
    "outflows": -0.24,
    "rejection": -0.18,
    "regulatory": -0.2,
    "resistance": -0.12,
    "risk": -0.12,
    "selloff": -0.32,
    "slowdown": -0.16,
}


def score_text(text: str) -> float:
    lowered = text.lower()
    score = 0.0
    for term, weight in POSITIVE_TERMS.items():
        if term in lowered:
            score += weight
    for term, weight in NEGATIVE_TERMS.items():
        if term in lowered:
            score += weight
    return round(max(-1.0, min(1.0, score)), 4)


def classification(score: float) -> str:
    if score >= 0.15:
        return "bullish"
    if score <= -0.15:
        return "bearish"
    return "neutral"


def impact_level(score: float, confidence: float = 0.5) -> str:
    weighted_score = abs(score) * max(0.25, confidence)
    if weighted_score >= 0.35:
        return "high"
    if weighted_score >= 0.12:
        return "medium"
    return "low"
