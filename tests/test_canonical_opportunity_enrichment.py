from __future__ import annotations

from datetime import datetime, timedelta, timezone

from alpha_velocity.market.bars import Bar
from alpha_velocity.marketplace import OpportunityMarketplace
from alpha_velocity.opportunity import (
    LifecycleStage,
    Opportunity,
    assemble_opportunity,
)
from alpha_velocity.opportunity_ranking import OpportunityRanker
import alpha_velocity.ranking.models as legacy_ranking_models


def _bars(observation_time: datetime, count: int, step_days: int = 1) -> list[Bar]:
    bars: list[Bar] = []
    for i in range(count):
        ts = observation_time - timedelta(days=(count - i) * step_days)
        open_price = 100.0 + i
        bars.append(
            Bar(
                timestamp=ts,
                open=open_price,
                high=open_price + 2.0,
                low=open_price - 1.0,
                close=open_price + 1.0,
                volume=1_000_000.0,
            )
        )
    return bars


def _make_opp(symbol: str, observation_time: datetime) -> Opportunity:
    return assemble_opportunity(
        daily_bars=_bars(observation_time, 80, 1),
        weekly_bars=_bars(observation_time, 80, 7),
        benchmark_bars=_bars(observation_time, 80, 1),
        sector_bars=_bars(observation_time, 80, 1),
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id=f"sample-{symbol.lower()}",
        symbol=symbol,
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="UNIV-TEST",
        warehouse_manifest_hash="WH",
        dataset_manifest_hash="DS",
        source_record_ids=["SRC-1", "SRC-2"],
    )


def test_one_authoritative_canonical_opportunity_class() -> None:
    assert Opportunity.__module__ == "alpha_velocity.opportunity.models"
    assert legacy_ranking_models.__name__.endswith("alpha_velocity.ranking.models")


def test_old_payload_still_loads_with_defaults() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("AAPL", now)
    payload = opp.to_dict()
    for key in (
        "thesis_identity",
        "expressions",
        "lifecycle",
        "research_horizon",
        "primary_repricing_horizon",
        "tactical_swing_horizon",
        "execution_horizon",
        "recognition_profile",
        "claim_set",
        "change_windows",
        "assumptions",
        "invalidation_profile",
        "research_conviction",
        "capital_conviction",
    ):
        payload.pop(key, None)
    payload["schema_version"] = "1.0.0"

    loaded = Opportunity.from_dict(payload)
    assert loaded.security_id == opp.security_id
    assert loaded.schema_version == "1.0.0"
    assert loaded.thesis_identity is None
    assert loaded.research_conviction.state.value == "MEDIUM"


def test_enriched_round_trip_preserves_fields() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("TOP2", now)
    reloaded = Opportunity.from_dict(opp.to_dict())

    assert reloaded.thesis_identity is not None
    assert len(reloaded.expressions) >= 2
    assert reloaded.claim_set.why_now
    assert reloaded.research_horizon is not None
    assert reloaded.execution_horizon is not None


def test_thesis_and_expressions_are_distinct() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("TOP2", now)

    assert opp.thesis_identity is not None
    assert opp.thesis_identity.thesis_id.startswith("THESIS-")
    assert len(opp.expressions) >= 2
    assert all(expression.expression_id for expression in opp.expressions)


def test_lifecycle_transition_is_auditable_and_not_execution_authority() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("AAPL", now)

    transitioned = opp.transition_lifecycle(LifecycleStage.PRIMARY_MOVE, "Confirmed by updated evidence")

    assert transitioned.lifecycle is not None
    assert transitioned.lifecycle.prior_stage is not None
    assert transitioned.lifecycle.evidence_lineage
    assert transitioned.risk_eligible == opp.risk_eligible
    assert transitioned.governance_eligible == opp.governance_eligible


def test_four_horizons_stay_independent() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("TOP1", now)

    assert opp.research_horizon is not None
    assert opp.primary_repricing_horizon is not None
    assert opp.tactical_swing_horizon is not None
    assert opp.execution_horizon is not None
    assert opp.research_horizon.status != opp.execution_horizon.status


def test_research_conviction_can_exceed_capital_conviction() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("VAL1", now)

    assert opp.research_conviction.state.value in {"HIGH", "VERY_HIGH"}
    assert opp.capital_conviction.state.value in {"LOW", "MEDIUM"}


def test_why_now_why_not_and_unknowns_preserve_lineage() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    weak = _make_opp("WEAK", now)

    assert weak.claim_set.why_now
    assert weak.claim_set.unknown
    assert weak.claim_set.unknown[0].evidence_lineage


def test_assumptions_and_invalidations_are_explicit() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("EXC1", now)

    assert opp.assumptions
    assert all(assumption.validation_status.value for assumption in opp.assumptions)
    assert opp.invalidation_profile.thesis_invalidation
    assert opp.invalidation_profile.tactical_invalidation
    assert opp.invalidation_profile.execution_invalidation
    assert opp.invalidation_profile.data_invalidation


def test_change_windows_deterministic_serialization() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opp = _make_opp("AAPL", now)
    left = Opportunity.from_dict(opp.to_dict()).to_json()
    right = Opportunity.from_dict(opp.to_dict()).to_json()
    assert left == right


def test_ranking_backwards_compatible_shadow_default_zero() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opps = [_make_opp("AAPL", now), _make_opp("MSFT", now)]
    ranker = OpportunityRanker()

    baseline = ranker.rank(opps)
    zero_shadow = ranker.rank(
        opps,
        shadow_signals_by_opportunity={o.opportunity_id: {"demo": 99.0} for o in opps},
        ranking_shadow_influence_enabled=False,
        ranking_shadow_weight=0.0,
    )

    assert [r.opportunity_id for r in baseline.ranked_opportunities] == [
        r.opportunity_id for r in zero_shadow.ranked_opportunities
    ]


def test_marketplace_still_builds_review_and_top_five_counts() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    opportunities = [_make_opp(f"TRG{i}", now) for i in range(1, 13)]
    marketplace = OpportunityMarketplace()
    result = marketplace.organize(opportunities, now)

    assert len(result.committee_review_list) == 10
    assert len(result.top_five) == 5
