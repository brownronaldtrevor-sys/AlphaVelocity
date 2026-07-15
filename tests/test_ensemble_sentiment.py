from datetime import datetime, timedelta

import pytest

from alpha_velocity.ensemble.auditor import EnsembleAuditError, EnsembleAuditor
from alpha_velocity.ensemble.combiner import CalibratedWeightedEnsemble
from alpha_velocity.ensemble.models import ModelPrediction
from alpha_velocity.sentiment.engineer import PointInTimeSentimentEngineer
from alpha_velocity.sentiment.models import SentimentDocument, SentimentSource


def test_ensemble_rejects_same_family_concentration():
    t = datetime(2026, 1, 1)
    preds = [
        ModelPrediction("m1", t, .6, .02, .2, .2, .3, "R", "technical"),
        ModelPrediction("m2", t, .7, .03, .2, .2, .3, "R", "technical"),
    ]
    with pytest.raises(EnsembleAuditError):
        CalibratedWeightedEnsemble().combine(preds)


def test_ensemble_combines_diverse_models():
    t = datetime(2026, 1, 1)
    preds = [
        ModelPrediction("m1", t, .6, .02, .2, .2, .3, "R", "technical"),
        ModelPrediction("m2", t, .7, .03, .2, .2, .3, "R", "sentiment"),
    ]
    out = CalibratedWeightedEnsemble().combine(preds)
    assert 0 <= out.probability_up <= 1
    assert len(out.active_models) == 2


def test_sentiment_is_point_in_time():
    engineer = PointInTimeSentimentEngineer()
    t0 = datetime(2026, 1, 1)
    docs = [
        SentimentDocument(
            "d1", SentimentSource.EARNINGS_CALL, "ABC",
            published_at=t0, available_at=t0 + timedelta(hours=1),
            text="Demand improved and pricing was strong."
        )
    ]
    before = engineer.transform(docs, "ABC", t0)
    after = engineer.transform(docs, "ABC", t0 + timedelta(hours=2))
    assert before == []
    assert len(after) == 1
