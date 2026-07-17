from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class ValidationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNTESTED = "UNTESTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class ThesisType(str, Enum):
    SWING_REPRICING = "SWING_REPRICING"
    TURNAROUND = "TURNAROUND"
    INDUSTRY_RECOVERY = "INDUSTRY_RECOVERY"
    CAPITAL_STRUCTURE_IMPROVEMENT = "CAPITAL_STRUCTURE_IMPROVEMENT"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    ACTIVIST = "ACTIVIST"
    ASSET_VALUE = "ASSET_VALUE"
    EARNINGS_INFLECTION = "EARNINGS_INFLECTION"
    SPECIAL_SITUATION = "SPECIAL_SITUATION"
    USER_HYPOTHESIS = "USER_HYPOTHESIS"


class ThesisStatus(str, Enum):
    ACTIVE = "ACTIVE"
    WATCH = "WATCH"
    INVALIDATED = "INVALIDATED"
    CLOSED = "CLOSED"


class ExpressionType(str, Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    BASKET = "BASKET"
    PEER = "PEER"
    EXISTING_HOLDING = "EXISTING_HOLDING"
    WATCHLIST_SECURITY = "WATCHLIST_SECURITY"


class LifecycleStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    RESEARCH = "RESEARCH"
    WATCH = "WATCH"
    STARTER = "STARTER"
    PRIMARY_MOVE = "PRIMARY_MOVE"
    MANAGE = "MANAGE"
    HARVEST = "HARVEST"
    EXIT_REVIEW = "EXIT_REVIEW"
    CLOSED = "CLOSED"
    INVALIDATED = "INVALIDATED"


class RecognitionState(str, Enum):
    UNKNOWN = "UNKNOWN"
    BEFORE_RECOGNITION = "BEFORE_RECOGNITION"
    BEGINNING = "BEGINNING"
    ACCELERATING = "ACCELERATING"
    CONFIRMED = "CONFIRMED"
    MATURE = "MATURE"
    EXTENDED = "EXTENDED"
    EXHAUSTING = "EXHAUSTING"
    FAILED = "FAILED"
    ROLLING_OVER = "ROLLING_OVER"


class AssumptionStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNTESTED = "UNTESTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class ConvictionState(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True, order=True)
class EvidenceClaim:
    claim_id: str
    text: str
    claim_type: str
    source: str
    observation_time: datetime
    available_at: datetime
    confidence: float
    validation_status: ValidationStatus
    evidence_lineage: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type,
            "source": self.source,
            "observation_time": self.observation_time.isoformat(),
            "available_at": self.available_at.isoformat(),
            "confidence": self.confidence,
            "validation_status": self.validation_status.value,
            "evidence_lineage": list(self.evidence_lineage),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "EvidenceClaim":
        return cls(
            claim_id=str(payload.get("claim_id") or ""),
            text=str(payload.get("text") or ""),
            claim_type=str(payload.get("claim_type") or ""),
            source=str(payload.get("source") or "UNKNOWN"),
            observation_time=_parse_datetime(payload.get("observation_time")) or fallback_time,
            available_at=_parse_datetime(payload.get("available_at")) or fallback_time,
            confidence=float(payload.get("confidence", 0.0)),
            validation_status=ValidationStatus(str(payload.get("validation_status") or ValidationStatus.UNKNOWN.value)),
            evidence_lineage=tuple(payload.get("evidence_lineage") or ()),
        )


@dataclass(frozen=True)
class ThesisIdentity:
    thesis_id: str
    thesis_name: str
    thesis_summary: str
    thesis_type: ThesisType
    origin: str
    created_at: datetime
    observation_time: datetime
    available_at: datetime
    version: str
    status: ThesisStatus
    evidence_lineage: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "thesis_id": self.thesis_id,
            "thesis_name": self.thesis_name,
            "thesis_summary": self.thesis_summary,
            "thesis_type": self.thesis_type.value,
            "origin": self.origin,
            "created_at": self.created_at.isoformat(),
            "observation_time": self.observation_time.isoformat(),
            "available_at": self.available_at.isoformat(),
            "version": self.version,
            "status": self.status.value,
            "evidence_lineage": list(self.evidence_lineage),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "ThesisIdentity":
        return cls(
            thesis_id=str(payload.get("thesis_id") or ""),
            thesis_name=str(payload.get("thesis_name") or ""),
            thesis_summary=str(payload.get("thesis_summary") or ""),
            thesis_type=ThesisType(str(payload.get("thesis_type") or ThesisType.SWING_REPRICING.value)),
            origin=str(payload.get("origin") or "SCANNER"),
            created_at=_parse_datetime(payload.get("created_at")) or fallback_time,
            observation_time=_parse_datetime(payload.get("observation_time")) or fallback_time,
            available_at=_parse_datetime(payload.get("available_at")) or fallback_time,
            version=str(payload.get("version") or "1"),
            status=ThesisStatus(str(payload.get("status") or ThesisStatus.ACTIVE.value)),
            evidence_lineage=tuple(payload.get("evidence_lineage") or ()),
        )


@dataclass(frozen=True, order=True)
class OpportunityExpression:
    expression_id: str
    security_id: str = ""
    basket_id: str = ""
    symbol: str = ""
    expression_type: ExpressionType = ExpressionType.EQUITY
    role: str = "PRIMARY"
    attractiveness: float = 0.0
    research_confidence: float = 0.0
    liquidity: float = 0.0
    implementation_cost: float = 0.0
    current_actionability: str = "RESEARCH_ONLY"
    relationship_to_thesis: str = ""
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    available_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "expression_id": self.expression_id,
            "security_id": self.security_id,
            "basket_id": self.basket_id,
            "symbol": self.symbol,
            "expression_type": self.expression_type.value,
            "role": self.role,
            "attractiveness": self.attractiveness,
            "research_confidence": self.research_confidence,
            "liquidity": self.liquidity,
            "implementation_cost": self.implementation_cost,
            "current_actionability": self.current_actionability,
            "relationship_to_thesis": self.relationship_to_thesis,
            "supporting_evidence": list(self.supporting_evidence),
            "contradictory_evidence": list(self.contradictory_evidence),
            "available_at": self.available_at.isoformat(),
            "validation_status": self.validation_status.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "OpportunityExpression":
        return cls(
            expression_id=str(payload.get("expression_id") or ""),
            security_id=str(payload.get("security_id") or ""),
            basket_id=str(payload.get("basket_id") or ""),
            symbol=str(payload.get("symbol") or ""),
            expression_type=ExpressionType(str(payload.get("expression_type") or ExpressionType.EQUITY.value)),
            role=str(payload.get("role") or "PRIMARY"),
            attractiveness=float(payload.get("attractiveness", 0.0)),
            research_confidence=float(payload.get("research_confidence", 0.0)),
            liquidity=float(payload.get("liquidity", 0.0)),
            implementation_cost=float(payload.get("implementation_cost", 0.0)),
            current_actionability=str(payload.get("current_actionability") or "RESEARCH_ONLY"),
            relationship_to_thesis=str(payload.get("relationship_to_thesis") or ""),
            supporting_evidence=tuple(payload.get("supporting_evidence") or ()),
            contradictory_evidence=tuple(payload.get("contradictory_evidence") or ()),
            available_at=_parse_datetime(payload.get("available_at")) or fallback_time,
            validation_status=ValidationStatus(str(payload.get("validation_status") or ValidationStatus.UNKNOWN.value)),
        )


@dataclass(frozen=True)
class OpportunityLifecycle:
    current_stage: LifecycleStage
    prior_stage: LifecycleStage | None
    stage_changed_at: datetime
    stage_reason: str
    required_confirmation: tuple[str, ...] = ()
    advancement_conditions: tuple[str, ...] = ()
    regression_conditions: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    evidence_lineage: tuple[str, ...] = ()

    def transition(self, new_stage: LifecycleStage, reason: str, changed_at: datetime) -> "OpportunityLifecycle":
        if changed_at < self.stage_changed_at:
            raise ValueError("lifecycle transition time cannot move backwards")
        if self.current_stage == LifecycleStage.INVALIDATED and new_stage != LifecycleStage.INVALIDATED:
            raise ValueError("cannot transition out of INVALIDATED stage")
        return OpportunityLifecycle(
            current_stage=new_stage,
            prior_stage=self.current_stage,
            stage_changed_at=changed_at,
            stage_reason=reason,
            required_confirmation=self.required_confirmation,
            advancement_conditions=self.advancement_conditions,
            regression_conditions=self.regression_conditions,
            invalidation_conditions=self.invalidation_conditions,
            evidence_lineage=self.evidence_lineage + (f"{self.current_stage.value}->{new_stage.value}@{changed_at.isoformat()}",),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_stage": self.current_stage.value,
            "prior_stage": self.prior_stage.value if self.prior_stage else None,
            "stage_changed_at": self.stage_changed_at.isoformat(),
            "stage_reason": self.stage_reason,
            "required_confirmation": list(self.required_confirmation),
            "advancement_conditions": list(self.advancement_conditions),
            "regression_conditions": list(self.regression_conditions),
            "invalidation_conditions": list(self.invalidation_conditions),
            "evidence_lineage": list(self.evidence_lineage),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "OpportunityLifecycle":
        prior = payload.get("prior_stage")
        return cls(
            current_stage=LifecycleStage(str(payload.get("current_stage") or LifecycleStage.DISCOVERY.value)),
            prior_stage=LifecycleStage(str(prior)) if prior else None,
            stage_changed_at=_parse_datetime(payload.get("stage_changed_at")) or fallback_time,
            stage_reason=str(payload.get("stage_reason") or ""),
            required_confirmation=tuple(payload.get("required_confirmation") or ()),
            advancement_conditions=tuple(payload.get("advancement_conditions") or ()),
            regression_conditions=tuple(payload.get("regression_conditions") or ()),
            invalidation_conditions=tuple(payload.get("invalidation_conditions") or ()),
            evidence_lineage=tuple(payload.get("evidence_lineage") or ()),
        )


@dataclass(frozen=True)
class HorizonAssessment:
    status: str
    attractiveness: float
    confidence: float
    expected_realization_window: str
    expected_move_range: str
    downside_range: str
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    invalidation: str = ""
    observation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    available_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    calibration_status: str = "UNCALIBRATED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "attractiveness": self.attractiveness,
            "confidence": self.confidence,
            "expected_realization_window": self.expected_realization_window,
            "expected_move_range": self.expected_move_range,
            "downside_range": self.downside_range,
            "supporting_evidence": list(self.supporting_evidence),
            "contradictory_evidence": list(self.contradictory_evidence),
            "required_confirmation": list(self.required_confirmation),
            "invalidation": self.invalidation,
            "observation_time": self.observation_time.isoformat(),
            "available_at": self.available_at.isoformat(),
            "validation_status": self.validation_status.value,
            "calibration_status": self.calibration_status,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "HorizonAssessment":
        return cls(
            status=str(payload.get("status") or "UNKNOWN"),
            attractiveness=float(payload.get("attractiveness", 0.0)),
            confidence=float(payload.get("confidence", 0.0)),
            expected_realization_window=str(payload.get("expected_realization_window") or ""),
            expected_move_range=str(payload.get("expected_move_range") or ""),
            downside_range=str(payload.get("downside_range") or ""),
            supporting_evidence=tuple(payload.get("supporting_evidence") or ()),
            contradictory_evidence=tuple(payload.get("contradictory_evidence") or ()),
            required_confirmation=tuple(payload.get("required_confirmation") or ()),
            invalidation=str(payload.get("invalidation") or ""),
            observation_time=_parse_datetime(payload.get("observation_time")) or fallback_time,
            available_at=_parse_datetime(payload.get("available_at")) or fallback_time,
            validation_status=ValidationStatus(str(payload.get("validation_status") or ValidationStatus.UNKNOWN.value)),
            calibration_status=str(payload.get("calibration_status") or "UNCALIBRATED"),
        )


@dataclass(frozen=True)
class RecognitionProfile:
    state: RecognitionState
    prior_state: RecognitionState | None
    direction: str
    velocity: float
    changed_at: datetime
    reason: str
    evidence: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    invalidation: str = ""
    applicable_horizon: str = ""
    confidence: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "prior_state": self.prior_state.value if self.prior_state else None,
            "direction": self.direction,
            "velocity": self.velocity,
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
            "evidence": list(self.evidence),
            "contradictions": list(self.contradictions),
            "required_confirmation": list(self.required_confirmation),
            "invalidation": self.invalidation,
            "applicable_horizon": self.applicable_horizon,
            "confidence": self.confidence,
            "validation_status": self.validation_status.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "RecognitionProfile":
        prior = payload.get("prior_state")
        return cls(
            state=RecognitionState(str(payload.get("state") or RecognitionState.UNKNOWN.value)),
            prior_state=RecognitionState(str(prior)) if prior else None,
            direction=str(payload.get("direction") or "FLAT"),
            velocity=float(payload.get("velocity", 0.0)),
            changed_at=_parse_datetime(payload.get("changed_at")) or fallback_time,
            reason=str(payload.get("reason") or ""),
            evidence=tuple(payload.get("evidence") or ()),
            contradictions=tuple(payload.get("contradictions") or ()),
            required_confirmation=tuple(payload.get("required_confirmation") or ()),
            invalidation=str(payload.get("invalidation") or ""),
            applicable_horizon=str(payload.get("applicable_horizon") or ""),
            confidence=float(payload.get("confidence", 0.0)),
            validation_status=ValidationStatus(str(payload.get("validation_status") or ValidationStatus.UNKNOWN.value)),
        )


@dataclass(frozen=True)
class ClaimSet:
    why_now: tuple[EvidenceClaim, ...] = ()
    why_not_now: tuple[EvidenceClaim, ...] = ()
    positive_changes: tuple[EvidenceClaim, ...] = ()
    negative_changes: tuple[EvidenceClaim, ...] = ()
    missing_information: tuple[EvidenceClaim, ...] = ()
    required_confirmation: tuple[EvidenceClaim, ...] = ()
    known: tuple[EvidenceClaim, ...] = ()
    unknown: tuple[EvidenceClaim, ...] = ()
    what_would_change_my_mind: tuple[EvidenceClaim, ...] = ()
    most_sensitive_assumption: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "why_now": [claim.to_dict() for claim in self.why_now],
            "why_not_now": [claim.to_dict() for claim in self.why_not_now],
            "positive_changes": [claim.to_dict() for claim in self.positive_changes],
            "negative_changes": [claim.to_dict() for claim in self.negative_changes],
            "missing_information": [claim.to_dict() for claim in self.missing_information],
            "required_confirmation": [claim.to_dict() for claim in self.required_confirmation],
            "known": [claim.to_dict() for claim in self.known],
            "unknown": [claim.to_dict() for claim in self.unknown],
            "what_would_change_my_mind": [claim.to_dict() for claim in self.what_would_change_my_mind],
            "most_sensitive_assumption": self.most_sensitive_assumption,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "ClaimSet":
        def parse_claims(key: str) -> tuple[EvidenceClaim, ...]:
            raw = payload.get(key) or ()
            return tuple(EvidenceClaim.from_dict(item, fallback_time) for item in raw)

        return cls(
            why_now=parse_claims("why_now"),
            why_not_now=parse_claims("why_not_now"),
            positive_changes=parse_claims("positive_changes"),
            negative_changes=parse_claims("negative_changes"),
            missing_information=parse_claims("missing_information"),
            required_confirmation=parse_claims("required_confirmation"),
            known=parse_claims("known"),
            unknown=parse_claims("unknown"),
            what_would_change_my_mind=parse_claims("what_would_change_my_mind"),
            most_sensitive_assumption=str(payload.get("most_sensitive_assumption") or ""),
        )


@dataclass(frozen=True)
class ChangeWindow:
    facts_changed: tuple[str, ...] = ()
    evidence_added: tuple[str, ...] = ()
    evidence_removed: tuple[str, ...] = ()
    thesis_strengthened: bool = False
    thesis_weakened: bool = False
    recognition_changed: bool = False
    lifecycle_changed: bool = False
    horizon_changed: bool = False
    unresolved_conflicts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts_changed": list(self.facts_changed),
            "evidence_added": list(self.evidence_added),
            "evidence_removed": list(self.evidence_removed),
            "thesis_strengthened": self.thesis_strengthened,
            "thesis_weakened": self.thesis_weakened,
            "recognition_changed": self.recognition_changed,
            "lifecycle_changed": self.lifecycle_changed,
            "horizon_changed": self.horizon_changed,
            "unresolved_conflicts": list(self.unresolved_conflicts),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ChangeWindow":
        return cls(
            facts_changed=tuple(payload.get("facts_changed") or ()),
            evidence_added=tuple(payload.get("evidence_added") or ()),
            evidence_removed=tuple(payload.get("evidence_removed") or ()),
            thesis_strengthened=bool(payload.get("thesis_strengthened", False)),
            thesis_weakened=bool(payload.get("thesis_weakened", False)),
            recognition_changed=bool(payload.get("recognition_changed", False)),
            lifecycle_changed=bool(payload.get("lifecycle_changed", False)),
            horizon_changed=bool(payload.get("horizon_changed", False)),
            unresolved_conflicts=tuple(payload.get("unresolved_conflicts") or ()),
        )


@dataclass(frozen=True)
class ChangeWindows:
    since_previous_observation: ChangeWindow = field(default_factory=ChangeWindow)
    one_day: ChangeWindow = field(default_factory=ChangeWindow)
    one_week: ChangeWindow = field(default_factory=ChangeWindow)
    one_month: ChangeWindow = field(default_factory=ChangeWindow)
    one_quarter: ChangeWindow = field(default_factory=ChangeWindow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "since_previous_observation": self.since_previous_observation.to_dict(),
            "one_day": self.one_day.to_dict(),
            "one_week": self.one_week.to_dict(),
            "one_month": self.one_month.to_dict(),
            "one_quarter": self.one_quarter.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ChangeWindows":
        return cls(
            since_previous_observation=ChangeWindow.from_dict(payload.get("since_previous_observation") or {}),
            one_day=ChangeWindow.from_dict(payload.get("one_day") or {}),
            one_week=ChangeWindow.from_dict(payload.get("one_week") or {}),
            one_month=ChangeWindow.from_dict(payload.get("one_month") or {}),
            one_quarter=ChangeWindow.from_dict(payload.get("one_quarter") or {}),
        )


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    statement: str
    category: str
    importance: float
    sensitivity: float
    dependency: str
    status: AssumptionStatus
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    last_reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    invalidation_condition: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement,
            "category": self.category,
            "importance": self.importance,
            "sensitivity": self.sensitivity,
            "dependency": self.dependency,
            "status": self.status.value,
            "supporting_evidence": list(self.supporting_evidence),
            "contradictory_evidence": list(self.contradictory_evidence),
            "validation_status": self.validation_status.value,
            "last_reviewed_at": self.last_reviewed_at.isoformat(),
            "invalidation_condition": self.invalidation_condition,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], fallback_time: datetime) -> "Assumption":
        return cls(
            assumption_id=str(payload.get("assumption_id") or ""),
            statement=str(payload.get("statement") or ""),
            category=str(payload.get("category") or ""),
            importance=float(payload.get("importance", 0.0)),
            sensitivity=float(payload.get("sensitivity", 0.0)),
            dependency=str(payload.get("dependency") or ""),
            status=AssumptionStatus(str(payload.get("status") or AssumptionStatus.UNKNOWN.value)),
            supporting_evidence=tuple(payload.get("supporting_evidence") or ()),
            contradictory_evidence=tuple(payload.get("contradictory_evidence") or ()),
            validation_status=ValidationStatus(str(payload.get("validation_status") or ValidationStatus.UNKNOWN.value)),
            last_reviewed_at=_parse_datetime(payload.get("last_reviewed_at")) or fallback_time,
            invalidation_condition=str(payload.get("invalidation_condition") or ""),
        )


@dataclass(frozen=True)
class InvalidationProfile:
    thesis_invalidation: tuple[str, ...] = ()
    tactical_invalidation: tuple[str, ...] = ()
    execution_invalidation: tuple[str, ...] = ()
    data_invalidation: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "thesis_invalidation": list(self.thesis_invalidation),
            "tactical_invalidation": list(self.tactical_invalidation),
            "execution_invalidation": list(self.execution_invalidation),
            "data_invalidation": list(self.data_invalidation),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InvalidationProfile":
        return cls(
            thesis_invalidation=tuple(payload.get("thesis_invalidation") or ()),
            tactical_invalidation=tuple(payload.get("tactical_invalidation") or ()),
            execution_invalidation=tuple(payload.get("execution_invalidation") or ()),
            data_invalidation=tuple(payload.get("data_invalidation") or ()),
        )


@dataclass(frozen=True)
class ConvictionAssessment:
    state: ConvictionState
    confidence: float
    evidence: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    applicable_horizon: str = ""
    required_confirmation: tuple[str, ...] = ()
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "contradictions": list(self.contradictions),
            "applicable_horizon": self.applicable_horizon,
            "required_confirmation": list(self.required_confirmation),
            "validation_status": self.validation_status.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConvictionAssessment":
        return cls(
            state=ConvictionState(str(payload.get("state") or ConvictionState.MEDIUM.value)),
            confidence=float(payload.get("confidence", 0.0)),
            evidence=tuple(payload.get("evidence") or ()),
            contradictions=tuple(payload.get("contradictions") or ()),
            applicable_horizon=str(payload.get("applicable_horizon") or ""),
            required_confirmation=tuple(payload.get("required_confirmation") or ()),
            validation_status=ValidationStatus(str(payload.get("validation_status") or ValidationStatus.UNKNOWN.value)),
        )


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    security_id: str
    symbol: str
    observation_time: datetime
    data_available_through: datetime
    universe_snapshot_id: str
    benchmark_symbol: str
    sector: str
    industry: str
    market_regime: str
    sector_regime: str
    weekly_trend_state: str
    weekly_range_position: float
    weekly_support_levels: tuple[dict[str, Any], ...]
    weekly_resistance_levels: tuple[dict[str, Any], ...]
    weekly_breakout_level: float
    weekly_invalidation_level: float
    weekly_volatility_state: str
    weekly_relative_strength: float
    weekly_structure_quality: float
    daily_trend_state: str
    daily_range_position: float
    daily_support_levels: tuple[dict[str, Any], ...]
    daily_resistance_levels: tuple[dict[str, Any], ...]
    daily_breakout_level: float
    daily_invalidation_level: float
    daily_volatility_state: str
    daily_relative_strength: float
    daily_structure_quality: float
    setup_type: str
    trigger_state: str
    breakout_distance_pct: float
    distance_to_support_pct: float
    distance_to_resistance_pct: float
    volatility_contraction: float
    volatility_expansion: float
    relative_volume: float
    close_quality: float
    failed_breakout: bool
    failed_breakdown: bool
    multi_timeframe_alignment: str
    close_price: float
    average_daily_dollar_volume: float
    average_daily_volume: float
    spread_estimate_bps: float
    atr_pct: float
    capacity_warning: bool
    known_catalysts: tuple[dict[str, Any], ...]
    next_known_event_time: datetime | None
    catalyst_risk: str
    event_data_available_at: datetime
    probability_estimate: float | None
    expected_upside_pct: float | None
    expected_downside_pct: float | None
    expected_holding_days: float | None
    estimated_cost_bps: float | None
    uncertainty_score: float
    calibration_status: str
    expected_value_score: float
    opportunity_cost_rank: int | None
    correlation_bucket: str
    concentration_bucket: str
    current_position_weight: float
    proposed_weight: float | None = None
    primary_invalidation_price: float = 0.0
    thesis_invalidation_reasons: tuple[str, ...] = ()
    liquidity_risk: str = "low"
    gap_risk: str = "low"
    model_disagreement: bool = False
    governance_eligible: bool = True
    risk_eligible: bool = True
    feature_values: dict[str, float] = field(default_factory=dict)
    feature_versions: dict[str, str] = field(default_factory=dict)
    model_versions: dict[str, str] = field(default_factory=dict)
    warehouse_manifest_hash: str = ""
    dataset_manifest_hash: str = ""
    source_record_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)

    thesis_identity: ThesisIdentity | None = None
    expressions: tuple[OpportunityExpression, ...] = ()
    lifecycle: OpportunityLifecycle | None = None
    research_horizon: HorizonAssessment | None = None
    primary_repricing_horizon: HorizonAssessment | None = None
    tactical_swing_horizon: HorizonAssessment | None = None
    execution_horizon: HorizonAssessment | None = None
    recognition_profile: RecognitionProfile | None = None
    claim_set: ClaimSet = field(default_factory=ClaimSet)
    change_windows: ChangeWindows = field(default_factory=ChangeWindows)
    assumptions: tuple[Assumption, ...] = ()
    invalidation_profile: InvalidationProfile = field(default_factory=InvalidationProfile)
    research_conviction: ConvictionAssessment = field(
        default_factory=lambda: ConvictionAssessment(state=ConvictionState.MEDIUM, confidence=0.0)
    )
    capital_conviction: ConvictionAssessment = field(
        default_factory=lambda: ConvictionAssessment(state=ConvictionState.LOW, confidence=0.0)
    )

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "2.1.0"

    def __post_init__(self) -> None:
        if self.data_available_through > self.observation_time:
            raise ValueError("data_available_through cannot exceed observation_time")
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.data_available_through.tzinfo is None:
            raise ValueError("data_available_through must be timezone-aware")
        if self.event_data_available_at > self.observation_time:
            raise ValueError("event_data_available_at cannot exceed observation_time")

        object.__setattr__(self, "weekly_support_levels", self._coerce_sequence(self.weekly_support_levels))
        object.__setattr__(self, "weekly_resistance_levels", self._coerce_sequence(self.weekly_resistance_levels))
        object.__setattr__(self, "daily_support_levels", self._coerce_sequence(self.daily_support_levels))
        object.__setattr__(self, "daily_resistance_levels", self._coerce_sequence(self.daily_resistance_levels))
        object.__setattr__(self, "known_catalysts", self._coerce_sequence(self.known_catalysts))
        object.__setattr__(self, "thesis_invalidation_reasons", self._coerce_sequence(self.thesis_invalidation_reasons))
        object.__setattr__(self, "source_record_ids", self._coerce_sequence(self.source_record_ids))
        object.__setattr__(self, "warnings", self._coerce_sequence(self.warnings))
        object.__setattr__(self, "expressions", tuple(sorted(self._coerce_sequence(self.expressions))))
        object.__setattr__(self, "assumptions", tuple(self._coerce_sequence(self.assumptions)))

        for catalyst in self.known_catalysts:
            if not isinstance(catalyst, Mapping):
                continue
            occurred_at = catalyst.get("occurred_at")
            available_at = catalyst.get("available_at")
            if occurred_at is not None and occurred_at > self.observation_time:
                raise ValueError("future catalyst evidence is not permitted")
            if available_at is not None and available_at > self.observation_time:
                raise ValueError("future catalyst availability is not permitted")

        if (
            self.probability_estimate is None
            or self.expected_upside_pct is None
            or self.expected_downside_pct is None
            or self.expected_holding_days is None
            or self.estimated_cost_bps is None
        ):
            self._set_uncalibrated()

    def _set_uncalibrated(self) -> None:
        if self.calibration_status != "CALIBRATED":
            object.__setattr__(self, "calibration_status", "UNCALIBRATED")
        if self.expected_value_score != 0.0:
            object.__setattr__(self, "expected_value_score", 0.0)

    @staticmethod
    def _coerce_sequence(value: Any) -> tuple[Any, ...]:
        if value is None:
            return ()
        if isinstance(value, tuple):
            return value
        if isinstance(value, list):
            return tuple(value)
        return (value,)

    def transition_lifecycle(self, new_stage: LifecycleStage, reason: str, changed_at: datetime | None = None) -> "Opportunity":
        if changed_at is None:
            changed_at = self.observation_time
        current_lifecycle = self.lifecycle or OpportunityLifecycle(
            current_stage=LifecycleStage.DISCOVERY,
            prior_stage=None,
            stage_changed_at=self.observation_time,
            stage_reason="initialized",
        )
        return replace(self, lifecycle=current_lifecycle.transition(new_stage, reason, changed_at))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return _serialize_value(payload)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Opportunity":
        observation_time = _parse_datetime(payload.get("observation_time"))
        if observation_time is None:
            raise ValueError("observation_time is required")

        thesis_payload = payload.get("thesis_identity")
        lifecycle_payload = payload.get("lifecycle")
        research_horizon_payload = payload.get("research_horizon")
        primary_horizon_payload = payload.get("primary_repricing_horizon")
        tactical_horizon_payload = payload.get("tactical_swing_horizon")
        execution_horizon_payload = payload.get("execution_horizon")
        recognition_payload = payload.get("recognition_profile")
        claims_payload = payload.get("claim_set") or {}
        windows_payload = payload.get("change_windows") or {}
        invalidation_payload = payload.get("invalidation_profile") or {}
        research_conviction_payload = payload.get("research_conviction") or {}
        capital_conviction_payload = payload.get("capital_conviction") or {}

        expressions = tuple(
            OpportunityExpression.from_dict(item, observation_time)
            for item in (payload.get("expressions") or ())
        )
        assumptions = tuple(
            Assumption.from_dict(item, observation_time)
            for item in (payload.get("assumptions") or ())
        )

        return cls(
            opportunity_id=str(payload["opportunity_id"]),
            security_id=str(payload["security_id"]),
            symbol=str(payload["symbol"]),
            observation_time=observation_time,
            data_available_through=_parse_datetime(payload.get("data_available_through")) or observation_time,
            universe_snapshot_id=str(payload["universe_snapshot_id"]),
            benchmark_symbol=str(payload["benchmark_symbol"]),
            sector=str(payload["sector"]),
            industry=str(payload["industry"]),
            market_regime=str(payload["market_regime"]),
            sector_regime=str(payload["sector_regime"]),
            weekly_trend_state=str(payload["weekly_trend_state"]),
            weekly_range_position=float(payload["weekly_range_position"]),
            weekly_support_levels=tuple(payload.get("weekly_support_levels") or []),
            weekly_resistance_levels=tuple(payload.get("weekly_resistance_levels") or []),
            weekly_breakout_level=float(payload["weekly_breakout_level"]),
            weekly_invalidation_level=float(payload["weekly_invalidation_level"]),
            weekly_volatility_state=str(payload["weekly_volatility_state"]),
            weekly_relative_strength=float(payload["weekly_relative_strength"]),
            weekly_structure_quality=float(payload["weekly_structure_quality"]),
            daily_trend_state=str(payload["daily_trend_state"]),
            daily_range_position=float(payload["daily_range_position"]),
            daily_support_levels=tuple(payload.get("daily_support_levels") or []),
            daily_resistance_levels=tuple(payload.get("daily_resistance_levels") or []),
            daily_breakout_level=float(payload["daily_breakout_level"]),
            daily_invalidation_level=float(payload["daily_invalidation_level"]),
            daily_volatility_state=str(payload["daily_volatility_state"]),
            daily_relative_strength=float(payload["daily_relative_strength"]),
            daily_structure_quality=float(payload["daily_structure_quality"]),
            setup_type=str(payload["setup_type"]),
            trigger_state=str(payload["trigger_state"]),
            breakout_distance_pct=float(payload["breakout_distance_pct"]),
            distance_to_support_pct=float(payload["distance_to_support_pct"]),
            distance_to_resistance_pct=float(payload["distance_to_resistance_pct"]),
            volatility_contraction=float(payload["volatility_contraction"]),
            volatility_expansion=float(payload["volatility_expansion"]),
            relative_volume=float(payload["relative_volume"]),
            close_quality=float(payload["close_quality"]),
            failed_breakout=bool(payload["failed_breakout"]),
            failed_breakdown=bool(payload["failed_breakdown"]),
            multi_timeframe_alignment=str(payload["multi_timeframe_alignment"]),
            close_price=float(payload["close_price"]),
            average_daily_dollar_volume=float(payload["average_daily_dollar_volume"]),
            average_daily_volume=float(payload["average_daily_volume"]),
            spread_estimate_bps=float(payload["spread_estimate_bps"]),
            atr_pct=float(payload["atr_pct"]),
            capacity_warning=bool(payload["capacity_warning"]),
            known_catalysts=tuple(payload.get("known_catalysts") or []),
            next_known_event_time=_parse_datetime(payload.get("next_known_event_time")),
            catalyst_risk=str(payload["catalyst_risk"]),
            event_data_available_at=_parse_datetime(payload.get("event_data_available_at")) or observation_time,
            probability_estimate=payload.get("probability_estimate"),
            expected_upside_pct=payload.get("expected_upside_pct"),
            expected_downside_pct=payload.get("expected_downside_pct"),
            expected_holding_days=payload.get("expected_holding_days"),
            estimated_cost_bps=payload.get("estimated_cost_bps"),
            uncertainty_score=float(payload["uncertainty_score"]),
            calibration_status=str(payload["calibration_status"]),
            expected_value_score=float(payload["expected_value_score"]),
            opportunity_cost_rank=payload.get("opportunity_cost_rank"),
            correlation_bucket=str(payload["correlation_bucket"]),
            concentration_bucket=str(payload["concentration_bucket"]),
            current_position_weight=float(payload["current_position_weight"]),
            proposed_weight=payload.get("proposed_weight"),
            primary_invalidation_price=float(payload.get("primary_invalidation_price", 0.0)),
            thesis_invalidation_reasons=tuple(payload.get("thesis_invalidation_reasons") or []),
            liquidity_risk=str(payload.get("liquidity_risk") or "low"),
            gap_risk=str(payload.get("gap_risk") or "low"),
            model_disagreement=bool(payload.get("model_disagreement", False)),
            governance_eligible=bool(payload.get("governance_eligible", True)),
            risk_eligible=bool(payload.get("risk_eligible", True)),
            feature_values=dict(payload.get("feature_values") or {}),
            feature_versions=dict(payload.get("feature_versions") or {}),
            model_versions=dict(payload.get("model_versions") or {}),
            warehouse_manifest_hash=str(payload.get("warehouse_manifest_hash") or ""),
            dataset_manifest_hash=str(payload.get("dataset_manifest_hash") or ""),
            source_record_ids=tuple(payload.get("source_record_ids") or []),
            warnings=tuple(payload.get("warnings") or []),
            thesis_identity=ThesisIdentity.from_dict(thesis_payload, observation_time) if isinstance(thesis_payload, Mapping) else None,
            expressions=expressions,
            lifecycle=OpportunityLifecycle.from_dict(lifecycle_payload, observation_time)
            if isinstance(lifecycle_payload, Mapping)
            else None,
            research_horizon=HorizonAssessment.from_dict(research_horizon_payload, observation_time)
            if isinstance(research_horizon_payload, Mapping)
            else None,
            primary_repricing_horizon=HorizonAssessment.from_dict(primary_horizon_payload, observation_time)
            if isinstance(primary_horizon_payload, Mapping)
            else None,
            tactical_swing_horizon=HorizonAssessment.from_dict(tactical_horizon_payload, observation_time)
            if isinstance(tactical_horizon_payload, Mapping)
            else None,
            execution_horizon=HorizonAssessment.from_dict(execution_horizon_payload, observation_time)
            if isinstance(execution_horizon_payload, Mapping)
            else None,
            recognition_profile=RecognitionProfile.from_dict(recognition_payload, observation_time)
            if isinstance(recognition_payload, Mapping)
            else None,
            claim_set=ClaimSet.from_dict(claims_payload, observation_time),
            change_windows=ChangeWindows.from_dict(windows_payload),
            assumptions=assumptions,
            invalidation_profile=InvalidationProfile.from_dict(invalidation_payload),
            research_conviction=ConvictionAssessment.from_dict(research_conviction_payload),
            capital_conviction=ConvictionAssessment.from_dict(capital_conviction_payload),
            created_at=_parse_datetime(payload.get("created_at")) or datetime.now(timezone.utc),
            schema_version=str(payload.get("schema_version", "1.0.0")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _serialize_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _serialize_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return value


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    text = str(value)
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
