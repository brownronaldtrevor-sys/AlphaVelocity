from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from alpha_velocity.sentiment.models import SentimentFeatureVector


@dataclass(frozen=True)
class AggregatedSentiment:
    issuer: str
    as_of: datetime
    tone: float
    uncertainty: float
    event_risk: float
    business_momentum: float
    management_credibility_proxy: float
    source_count: int
    disagreement: float


def aggregate_sentiment(
    vectors: list[SentimentFeatureVector],
    issuer: str,
    as_of: datetime,
) -> AggregatedSentiment:
    relevant = [v for v in vectors if v.issuer == issuer and v.as_of <= as_of]
    if not relevant:
        raise ValueError("No point-in-time sentiment vectors are available.")

    weights = [max(v.source_reliability, 1e-6) for v in relevant]
    total = sum(weights)

    def wavg(fn):
        return sum(w * fn(v) for w, v in zip(weights, relevant)) / total

    tone = wavg(lambda v: v.tone)
    uncertainty = wavg(lambda v: v.uncertainty + 0.05 * v.evasiveness)
    event_risk = wavg(lambda v: v.litigation_risk + v.liquidity_concern)
    business_momentum = wavg(
        lambda v: v.demand_strength + v.pricing_power + v.guidance_change
    )
    credibility = wavg(
        lambda v: max(
            -1.0,
            min(1.0, v.tone - v.evasiveness - 0.5 * v.contradiction)
        )
    )
    disagreement = max(v.tone for v in relevant) - min(v.tone for v in relevant)

    return AggregatedSentiment(
        issuer=issuer,
        as_of=as_of,
        tone=tone,
        uncertainty=uncertainty,
        event_risk=event_risk,
        business_momentum=business_momentum,
        management_credibility_proxy=credibility,
        source_count=len(relevant),
        disagreement=disagreement,
    )
