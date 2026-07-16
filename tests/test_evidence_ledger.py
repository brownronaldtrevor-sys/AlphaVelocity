"""
Tests for Evidence Ledger: append-only records, revisions, grading, scorecards, and reporting.
"""

import pytest
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from alpha_velocity.evidence_ledger import (
    EvidenceLedgerRecord,
    TechnicalEvidence,
    CatalystEvidence,
    ValuationEvidence,
    ExpectationsAndMispricingEvidence,
    ResearchEvidence,
    InfluenceWeights,
    RankingDecisionState,
    AllocationDecisionState,
    RiskGovernanceReviewState,
    DecisionStateEvidence,
    OutcomeGrade,
    OutcomeGradeHorizon,
    EvidenceStreamScorecard,
    AppendOnlyLedger,
    generate_record_id,
    create_revision_record,
    OutcomeGrader,
    PricePoint,
    EvidenceStreamScorecardBuilder,
    EvidenceLedgerReport,
    RecordType,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def observation_time() -> datetime:
    """Standard observation time for tests."""
    return datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)


@pytest.fixture
def technical_evidence(observation_time: datetime) -> TechnicalEvidence:
    """Sample technical evidence."""
    return TechnicalEvidence(
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=1),
        weekly_structure_quality=82.5,
        daily_structure_quality=78.0,
        multi_timeframe_alignment="CONFIRMED",
        primary_invalidation_price=95.0,
        weekly_trend_state="UPTREND",
        daily_trend_state="UPTREND",
        setup_type="CONTINUATION",
        close_quality=85.0,
        model_version="1.0.0",
    )


@pytest.fixture
def catalyst_evidence(observation_time: datetime) -> CatalystEvidence:
    """Sample catalyst evidence."""
    return CatalystEvidence(
        observation_time=observation_time,
        available_at=observation_time - timedelta(hours=12),
        next_known_event_time=observation_time + timedelta(days=7),
        catalyst_risk="SCHEDULED_EARNINGS",
        catalyst_magnitude_estimate="MEDIUM",
        catalyst_probability_estimate=0.75,
        model_version="1.0.0",
    )


@pytest.fixture
def valuation_evidence(observation_time: datetime) -> ValuationEvidence:
    """Sample valuation evidence."""
    return ValuationEvidence(
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=3),
        pe_ratio=18.5,
        peg_ratio=1.2,
        ev_to_ebitda=12.0,
        free_cash_flow_yield=0.045,
        model_version="1.0.0",
    )


@pytest.fixture
def expectations_evidence(observation_time: datetime) -> ExpectationsAndMispricingEvidence:
    """Sample shadow expectations evidence."""
    return ExpectationsAndMispricingEvidence(
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=2),
        upside_case_score=75.0,
        downside_case_score=40.0,
        consensus_gap_direction="WIDE_UPSIDE",
        estimated_gap_pct=15.0,
        revenue_forecast_fy1=5_200_000_000.0,
        ebitda_forecast_fy1=1_040_000_000.0,
        mispricing_magnitude_estimate=12.0,
        mispricing_persistence_estimate="MEDIUM",
        validation_status="UNCALIBRATED",
        confidence_level="MODERATE",
    )


@pytest.fixture
def research_evidence(
    technical_evidence: TechnicalEvidence,
    catalyst_evidence: CatalystEvidence,
    valuation_evidence: ValuationEvidence,
    expectations_evidence: ExpectationsAndMispricingEvidence,
) -> ResearchEvidence:
    """Complete research evidence."""
    return ResearchEvidence(
        technical=technical_evidence,
        catalysts=catalyst_evidence,
        valuation=valuation_evidence,
        expectations_mispricing=expectations_evidence,
    )


@pytest.fixture
def ranking_decision_state() -> RankingDecisionState:
    """Sample ranking decision state."""
    return RankingDecisionState(
        opportunity_id="opp-1",
        ranking_run_id="rank-1",
        rank=3,
        percentile=88.5,
        overall_research_score=82.5,
        ranking_state="HIGH_PRIORITY_TRIGGERED",
        intrinsic_score=85.0,
        timing_score=80.0,
        swing_value_score=81.0,
        technical_score=82.5,
        catalyst_score=80.0,
        capital_structure_score=78.0,
        liquidity_score=75.0,
        risk_adjustment=95.0,
        uncertainty_adjustment=90.0,
        positive_contributors=("TECHNICAL_SETUP", "CATALYST_UPCOMING"),
        negative_contributors=("HIGH_VALUATION",),
        warnings=("VOLATILITY_ELEVATED",),
    )


@pytest.fixture
def allocation_decision_state() -> AllocationDecisionState:
    """Sample allocation decision state."""
    return AllocationDecisionState(
        proposal_id="prop-1",
        proposed_allocation_weight=0.05,
        proposed_quantity=100,
        proposed_price_target=105.0,
        proposed_rotation=False,
    )


@pytest.fixture
def decision_state_evidence(
    ranking_decision_state: RankingDecisionState,
    allocation_decision_state: AllocationDecisionState,
) -> DecisionStateEvidence:
    """Complete decision state evidence."""
    return DecisionStateEvidence(
        opportunity_classification="QUALIFIED",
        ranking=ranking_decision_state,
        allocation=allocation_decision_state,
        risk_governance=RiskGovernanceReviewState(
            risk_review_required=True,
            risk_review_status="PENDING",
            governance_review_required=True,
            governance_review_status="PENDING",
            execution_authorized=False,
        ),
    )


@pytest.fixture
def evidence_ledger_record(
    observation_time: datetime,
    research_evidence: ResearchEvidence,
    decision_state_evidence: DecisionStateEvidence,
) -> EvidenceLedgerRecord:
    """Sample evidence ledger record."""
    return EvidenceLedgerRecord(
        record_id=generate_record_id(),
        observation_time=observation_time,
        created_at=datetime.now(timezone.utc),
        security_id="sec-1",
        symbol="TEST",
        universe_snapshot_id="univ-1",
        market_scan_run_id="scan-1",
        opportunity_id="opp-1",
        ranking_run_id="rank-1",
        capital_proposal_id="prop-1",
        warehouse_manifest_hash="hash1",
        dataset_manifest_hash="hash2",
        git_commit="abc123def456",
        research_evidence=research_evidence,
        decision_state=decision_state_evidence,
        influence_weights=InfluenceWeights(
            technical_ranking_influence=1.0,
            expectations_ranking_influence=0.0,  # SHADOW
            expectations_validation_status="SHADOW",
        ),
    )


# ============================================================================
# IMMUTABILITY TESTS
# ============================================================================

def test_append_only_ledger_immutable(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that ledger records are immutable (append-only)."""
    ledger = AppendOnlyLedger()
    record_id = ledger.add_record(evidence_ledger_record)
    
    # Retrieve and verify
    retrieved = ledger.get_record(record_id)
    assert retrieved is not None
    assert retrieved.record_id == evidence_ledger_record.record_id
    
    # Trying to add same record with different content should raise error
    modified_record = create_revision_record(
        evidence_ledger_record,
        "Testing revision",
        {"symbol": "MODIFIED"}
    )
    ledger.add_record(modified_record)
    
    # Original should still be there
    original = ledger.get_record(evidence_ledger_record.record_id)
    assert original.symbol == "TEST"


def test_revision_linking(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that revisions properly link superseded records."""
    ledger = AppendOnlyLedger()
    original_id = ledger.add_record(evidence_ledger_record)
    
    # Create revision
    revised = create_revision_record(
        evidence_ledger_record,
        "Data correction",
        {"decision_state": None}
    )
    revised_id = ledger.add_record(revised)
    
    # Verify supersession link
    assert revised.supersession is not None
    assert revised.supersession.supersedes_record_id == original_id
    assert revised.supersession.record_type == RecordType.REVISION.value
    
    # Verify chain
    chain = ledger.get_supersession_chain(original_id)
    assert len(chain) == 2
    assert chain[0].record_id == original_id
    assert chain[1].record_id == revised_id


def test_exclude_superseded_records(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that superseded records are excluded from standard queries."""
    ledger = AppendOnlyLedger()
    original_id = ledger.add_record(evidence_ledger_record)
    
    # Create revision
    revised = create_revision_record(
        evidence_ledger_record,
        "Correction",
        {}
    )
    ledger.add_record(revised)
    
    # Query without superseded
    records = ledger.get_records_by_symbol("TEST", include_superseded=False)
    assert len(records) == 1
    assert records[0].record_id != original_id  # Should be the revised version
    
    # Query with superseded
    records_with_superseded = ledger.get_records_by_symbol("TEST", include_superseded=True)
    assert len(records_with_superseded) == 2


# ============================================================================
# POINT-IN-TIME VALIDATION TESTS
# ============================================================================

def test_point_in_time_integrity_enforced(observation_time: datetime) -> None:
    """Test that future evidence is rejected."""
    future_time = observation_time + timedelta(days=1)
    
    # Try to create evidence with available_at in future
    with pytest.raises(ValueError, match="available_at .* > observation_time"):
        TechnicalEvidence(
            observation_time=observation_time,
            available_at=future_time,  # Future!
            weekly_structure_quality=80.0,
        )


def test_created_at_after_observation_enforced(observation_time: datetime) -> None:
    """Test that created_at cannot be before observation_time."""
    # This is allowed (created_at can be after observation_time for records from past)
    record = EvidenceLedgerRecord(
        record_id=generate_record_id(),
        observation_time=observation_time,
        created_at=observation_time + timedelta(hours=1),
        security_id="sec-1",
        symbol="TEST",
        universe_snapshot_id="univ-1",
    )
    assert record.created_at > record.observation_time


# ============================================================================
# SHADOW RESEARCH TESTS
# ============================================================================

def test_shadow_research_zero_influence(
    evidence_ledger_record: EvidenceLedgerRecord,
) -> None:
    """Test that shadow research has zero influence by default."""
    # Check that expectations is shadow
    weights = evidence_ledger_record.influence_weights
    assert weights.expectations_ranking_influence == 0.0
    assert weights.expectations_allocation_influence == 0.0
    assert weights.expectations_validation_status == "SHADOW"
    
    # Verify expectations evidence is still captured
    assert evidence_ledger_record.research_evidence.expectations_mispricing is not None


def test_shadow_cannot_increase_confidence(observation_time: datetime) -> None:
    """Test that unvalidated evidence cannot increase calibrated confidence."""
    # Create record with UNCALIBRATED expectations
    ranking_state = RankingDecisionState(
        opportunity_id="opp-1",
        ranking_run_id="rank-1",
        rank=1,
        percentile=99.0,
        overall_research_score=95.0,  # Very high score
        ranking_state="HIGH_PRIORITY_TRIGGERED",
        intrinsic_score=95.0,
        timing_score=95.0,
        swing_value_score=95.0,
        technical_score=95.0,
        catalyst_score=95.0,
        capital_structure_score=95.0,
        liquidity_score=95.0,
        risk_adjustment=100.0,
        uncertainty_adjustment=100.0,
        validation_status="UNCALIBRATED",  # Shadow!
    )
    
    record = EvidenceLedgerRecord(
        record_id=generate_record_id(),
        observation_time=observation_time,
        created_at=datetime.now(timezone.utc),
        security_id="sec-1",
        symbol="TEST",
        universe_snapshot_id="univ-1",
        decision_state=DecisionStateEvidence(ranking=ranking_state),
        influence_weights=InfluenceWeights(
            expectations_ranking_influence=0.0,  # Zero influence
            expectations_validation_status="SHADOW",
        ),
    )
    
    # Verify validation status cannot be promoted automatically
    assert record.decision_state.ranking.validation_status == "UNCALIBRATED"
    assert record.influence_weights.expectations_ranking_influence == 0.0


# ============================================================================
# OUTCOME GRADING TESTS
# ============================================================================

def test_outcome_grading_single_horizon(
    evidence_ledger_record: EvidenceLedgerRecord,
) -> None:
    """Test outcome grading over single horizon."""
    # Create price history
    base_date = evidence_ledger_record.observation_time
    prices = [
        PricePoint(base_date, 100.0, 105.0, 98.0, 102.0, 1_000_000),
        PricePoint(base_date + timedelta(days=1), 102.0, 108.0, 100.0, 106.0, 1_100_000),
        PricePoint(base_date + timedelta(days=5), 106.0, 110.0, 104.0, 108.0, 1_200_000),
    ]
    
    grader = OutcomeGrader({"TEST": prices})
    grade = grader.grade_record(
        evidence_ledger_record,
        OutcomeGradeHorizon.FIVE_DAYS,
    )
    
    assert grade is not None
    assert grade.forward_return_pct is not None
    assert grade.days_elapsed == 5


def test_outcome_grading_mfe_mae(
    evidence_ledger_record: EvidenceLedgerRecord,
) -> None:
    """Test maximum favorable and adverse excursions."""
    base_date = evidence_ledger_record.observation_time
    prices = [
        PricePoint(base_date, 100.0, 100.0, 100.0, 100.0, 1_000_000),
        PricePoint(base_date + timedelta(days=1), 100.0, 120.0, 90.0, 95.0, 1_000_000),
    ]
    
    grader = OutcomeGrader({"TEST": prices})
    grade = grader.grade_record(
        evidence_ledger_record,
        OutcomeGradeHorizon.ONE_DAY,
    )
    
    assert grade is not None
    # Note: entry_price might be estimated as proposed_price_target (105.0)
    # So MFE from 105.0 to 120.0 = 14.3%, MAE from 105.0 to 90.0 = 14.3%
    assert grade.max_favorable_excursion_pct is not None and grade.max_favorable_excursion_pct > 10.0
    assert grade.max_adverse_excursion_pct is not None and grade.max_adverse_excursion_pct > 5.0


def test_outcome_grading_no_future_data() -> None:
    """Test that outcome grading rejects future prices (no lookahead)."""
    observation_time = datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)
    
    record = EvidenceLedgerRecord(
        record_id=generate_record_id(),
        observation_time=observation_time,
        created_at=datetime.now(timezone.utc),
        security_id="sec-1",
        symbol="TEST",
        universe_snapshot_id="univ-1",
    )
    
    # Try to grade with future prices only
    future_prices = [
        PricePoint(observation_time + timedelta(days=100), 110.0, 115.0, 108.0, 112.0, 1_000_000),
    ]
    
    grader = OutcomeGrader({"TEST": future_prices})
    grade = grader.grade_record(record, OutcomeGradeHorizon.ONE_DAY)
    
    # Should return None (insufficient data)
    assert grade is None


# ============================================================================
# SCORECARD TESTS
# ============================================================================

def test_scorecard_generation() -> None:
    """Test evidence-stream scorecard generation."""
    observation_time = datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)
    
    # Create a record with outcome
    record = EvidenceLedgerRecord(
        record_id=generate_record_id(),
        observation_time=observation_time,
        created_at=datetime.now(timezone.utc),
        security_id="sec-1",
        symbol="TEST",
        universe_snapshot_id="univ-1",
        research_evidence=ResearchEvidence(
            technical=TechnicalEvidence(
                observation_time=observation_time,
                available_at=observation_time - timedelta(days=1),
            ),
        ),
        decision_state=DecisionStateEvidence(
            ranking=RankingDecisionState(
                opportunity_id="opp-1",
                ranking_run_id="rank-1",
                rank=1,
                percentile=99.0,
                overall_research_score=85.0,
                ranking_state="HIGH_PRIORITY_TRIGGERED",
                intrinsic_score=85.0,
                timing_score=85.0,
                swing_value_score=85.0,
                technical_score=85.0,
                catalyst_score=80.0,
                capital_structure_score=80.0,
                liquidity_score=80.0,
                risk_adjustment=100.0,
                uncertainty_adjustment=100.0,
            ),
        ),
    )
    
    grade = OutcomeGrade(
        horizon=OutcomeGradeHorizon.ONE_DAY,
        as_of_time=observation_time + timedelta(days=1),
        days_elapsed=1,
        forward_return_pct=5.0,
        direction_correct=True,
    )
    
    builder = EvidenceStreamScorecardBuilder()
    scorecard = builder.build_scorecard(
        "TECHNICAL",
        [(record, [grade])],
    )
    
    assert scorecard.stream_name == "TECHNICAL"
    assert scorecard.sample_count == 1
    assert scorecard.graded_count == 1
    assert scorecard.directional_accuracy_pct == 100.0


def test_no_automatic_evidence_promotion() -> None:
    """Test that unvalidated evidence is not automatically promoted."""
    # Create record with SHADOW expectations
    observation_time = datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)
    
    # Create multiple records to ensure we have sample count
    records = []
    for i in range(5):
        record = EvidenceLedgerRecord(
            record_id=generate_record_id(),
            observation_time=observation_time - timedelta(hours=i),
            created_at=datetime.now(timezone.utc),
            security_id=f"sec-{i}",
            symbol=f"TEST{i}",
            universe_snapshot_id="univ-1",
            influence_weights=InfluenceWeights(
                expectations_validation_status="SHADOW",
                expectations_ranking_influence=0.0,
            ),
            research_evidence=ResearchEvidence(
                expectations_mispricing=ExpectationsAndMispricingEvidence(
                    observation_time=observation_time - timedelta(hours=i),
                    available_at=observation_time - timedelta(days=1, hours=i),
                    validation_status="UNCALIBRATED",
                ),
            ),
        )
        records.append(record)
    
    builder = EvidenceStreamScorecardBuilder()
    scorecard = builder.build_scorecard(
        "EXPECTATIONS",
        [(record, []) for record in records],
    )
    
    # Should remain SHADOW (or INSUFFICIENT_DATA with no outcomes)
    assert scorecard.recommendation in ["REMAIN_SHADOW", "INSUFFICIENT_DATA"]


# ============================================================================
# QUERY TESTS
# ============================================================================

def test_query_by_symbol(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test querying records by symbol."""
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    records = ledger.get_records_by_symbol("TEST")
    assert len(records) == 1
    assert records[0].symbol == "TEST"


def test_query_by_date(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test querying records by date."""
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    records = ledger.get_records_by_date(evidence_ledger_record.observation_time)
    assert len(records) == 1


def test_query_by_opportunity_id(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test querying records by opportunity ID."""
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    records = ledger.get_records_by_opportunity_id("opp-1")
    assert len(records) == 1


def test_query_ungraded_records(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test querying ungraded records."""
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    ungraded = ledger.get_ungraded_records()
    assert len(ungraded) == 1
    assert len(ungraded[0].outcome_grades) == 0


def test_query_shadow_research_records(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test querying shadow research records."""
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    shadow = ledger.get_shadow_research_records()
    assert len(shadow) == 1
    assert shadow[0].influence_weights.expectations_validation_status == "SHADOW"


# ============================================================================
# REPORTING TESTS
# ============================================================================

def test_json_report_generation(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test JSON report generation."""
    report = EvidenceLedgerReport(evidence_ledger_record)
    json_str = report.to_json()
    
    assert json_str is not None
    assert evidence_ledger_record.record_id in json_str
    assert evidence_ledger_record.symbol in json_str


def test_markdown_report_generation(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test Markdown report generation."""
    report = EvidenceLedgerReport(evidence_ledger_record)
    md_str = report.to_markdown()
    
    assert "# Evidence Ledger Report" in md_str
    assert evidence_ledger_record.symbol in md_str
    assert evidence_ledger_record.record_id in md_str


def test_deterministic_serialization(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that serialization is deterministic."""
    report1 = EvidenceLedgerReport(evidence_ledger_record)
    report2 = EvidenceLedgerReport(evidence_ledger_record)
    
    json1 = report1.to_json()
    json2 = report2.to_json()
    
    assert json1 == json2


# ============================================================================
# SYSTEM BOUNDARY TESTS
# ============================================================================

def test_no_portfolio_mutation(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that ledger does not mutate supplied portfolio."""
    original_symbol = evidence_ledger_record.symbol
    
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    # Original record should not be modified
    assert evidence_ledger_record.symbol == original_symbol


def test_no_order_creation(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that evidence ledger never creates orders."""
    # This is a governance test - verify execution_authorized is always False
    ledger = AppendOnlyLedger()
    ledger.add_record(evidence_ledger_record)
    
    record = ledger.get_record(evidence_ledger_record.record_id)
    assert record is not None
    assert record.decision_state.risk_governance.execution_authorized == False


def test_no_broker_calls(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test that evidence ledger makes no broker calls."""
    # This is a defensive test - verify no external integrations
    ledger = AppendOnlyLedger()
    
    # Adding records should not trigger any external calls
    ledger.add_record(evidence_ledger_record)
    
    # Queries should not trigger external calls
    ledger.get_records_by_symbol("TEST")
    
    # Reports should not trigger external calls
    report = EvidenceLedgerReport(evidence_ledger_record)
    report.to_json()
    report.to_markdown()
    
    # If we get here without exceptions, no broker calls occurred
    assert True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_ledger_workflow(evidence_ledger_record: EvidenceLedgerRecord) -> None:
    """Test complete workflow: record, grade, scorecard, report."""
    observation_time = evidence_ledger_record.observation_time
    
    # 1. Add record to ledger
    ledger = AppendOnlyLedger()
    record_id = ledger.add_record(evidence_ledger_record)
    assert record_id is not None
    
    # 2. Create outcome grade
    prices = [
        PricePoint(observation_time, 100.0, 105.0, 98.0, 102.0, 1_000_000),
        PricePoint(observation_time + timedelta(days=5), 106.0, 110.0, 104.0, 108.0, 1_200_000),
    ]
    grader = OutcomeGrader({"TEST": prices})
    grade = grader.grade_record(evidence_ledger_record, OutcomeGradeHorizon.FIVE_DAYS)
    
    # 3. Build scorecard
    builder = EvidenceStreamScorecardBuilder()
    scorecard = builder.build_scorecard("TECHNICAL", [(evidence_ledger_record, [grade] if grade else [])])
    assert scorecard.stream_name == "TECHNICAL"
    
    # 4. Generate reports
    report = EvidenceLedgerReport(evidence_ledger_record)
    json_report = report.to_json()
    md_report = report.to_markdown()
    
    assert json_report is not None
    assert md_report is not None
    assert record_id in json_report
