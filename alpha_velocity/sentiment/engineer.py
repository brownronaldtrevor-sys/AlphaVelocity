from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from math import log1p

from alpha_velocity.sentiment.lexicons import (
    DEMAND, EVASIVE, LITIGATION, LIQUIDITY, NEGATIVE, POSITIVE, PRICING, UNCERTAINTY
)
from alpha_velocity.sentiment.models import (
    SentimentDocument,
    SentimentFeatureVector,
    SentimentSource,
)


class SentimentLineageError(RuntimeError):
    pass


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z\-']+", text.lower())


def _phrase_count(text: str, phrases: set[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(p) for p in phrases)


class PointInTimeSentimentEngineer:
    """
    Rule-based, point-in-time sentiment features.

    This is deliberately transparent. It does not claim predictive value until
    independently validated out of sample.
    """

    SOURCE_RELIABILITY = {
        SentimentSource.SEC_FILING: 0.95,
        SentimentSource.EARNINGS_CALL: 0.90,
        SentimentSource.PRESS_RELEASE: 0.75,
        SentimentSource.NEWS: 0.70,
        SentimentSource.ANALYST: 0.65,
        SentimentSource.SOCIAL: 0.35,
    }

    def transform(
        self,
        documents: list[SentimentDocument],
        issuer: str,
        as_of: datetime,
        prior_features: SentimentFeatureVector | None = None,
    ) -> list[SentimentFeatureVector]:
        eligible = [
            d for d in documents
            if d.issuer == issuer and d.available_at <= as_of
        ]
        if any(d.published_at > d.available_at for d in eligible):
            raise SentimentLineageError(
                "Document published_at cannot be after available_at."
            )

        grouped: dict[SentimentSource, list[SentimentDocument]] = {}
        for d in eligible:
            grouped.setdefault(d.source, []).append(d)

        vectors: list[SentimentFeatureVector] = []
        for source, docs in grouped.items():
            text = "\n".join(d.text for d in docs)
            toks = _tokens(text)
            n = max(len(toks), 1)
            counts = Counter(toks)

            pos = sum(counts[w] for w in POSITIVE)
            neg = sum(counts[w] for w in NEGATIVE)
            unc = sum(counts[w] for w in UNCERTAINTY)
            lit = _phrase_count(text, LITIGATION)
            liq = _phrase_count(text, LIQUIDITY)
            dem = _phrase_count(text, DEMAND)
            price = _phrase_count(text, PRICING)
            evasive = _phrase_count(text, EVASIVE)

            tone = (pos - neg) / n
            optimism = pos / n
            negativity = neg / n
            uncertainty = unc / n

            guidance_up = len(re.findall(r"(raise|increase|improve).{0,25}guidance", text.lower()))
            guidance_down = len(re.findall(r"(lower|reduce|withdraw|suspend).{0,25}guidance", text.lower()))
            guidance_change = (guidance_up - guidance_down) / max(len(docs), 1)

            source_reliability = self.SOURCE_RELIABILITY[source]

            # Novelty is transparent lexical rarity within the current batch only.
            # Production should compare against a point-in-time issuer/sector corpus.
            unique_ratio = len(set(toks)) / n
            novelty = min(1.0, unique_ratio * log1p(n) / 10.0)

            contradiction = 0.0
            if prior_features is not None and prior_features.source == source:
                contradiction = abs(tone - prior_features.tone) + abs(
                    guidance_change - prior_features.guidance_change
                )

            vectors.append(
                SentimentFeatureVector(
                    issuer=issuer,
                    as_of=as_of,
                    source=source,
                    document_count=len(docs),
                    tone=tone,
                    uncertainty=uncertainty,
                    optimism=optimism,
                    negativity=negativity,
                    litigation_risk=lit / max(len(docs), 1),
                    liquidity_concern=liq / max(len(docs), 1),
                    demand_strength=dem / max(len(docs), 1),
                    pricing_power=price / max(len(docs), 1),
                    guidance_change=guidance_change,
                    evasiveness=evasive / max(len(docs), 1),
                    novelty=novelty,
                    contradiction=contradiction,
                    source_reliability=source_reliability,
                )
            )

        return vectors
