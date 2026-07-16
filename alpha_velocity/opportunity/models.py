from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Mapping


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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

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

        for catalyst in self.known_catalysts:
            if not isinstance(catalyst, Mapping):
                continue
            occurred_at = catalyst.get("occurred_at")
            available_at = catalyst.get("available_at")
            if occurred_at is not None and occurred_at > self.observation_time:
                raise ValueError("future catalyst evidence is not permitted")
            if available_at is not None and available_at > self.observation_time:
                raise ValueError("future catalyst availability is not permitted")
        if self.probability_estimate is None or self.expected_upside_pct is None or self.expected_downside_pct is None or self.expected_holding_days is None or self.estimated_cost_bps is None:
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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observation_time"] = self._serialize_datetime(self.observation_time)
        payload["data_available_through"] = self._serialize_datetime(self.data_available_through)
        payload["next_known_event_time"] = self._serialize_datetime(self.next_known_event_time)
        payload["event_data_available_at"] = self._serialize_datetime(self.event_data_available_at)
        payload["created_at"] = self._serialize_datetime(self.created_at)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Opportunity":
        return cls(
            opportunity_id=str(payload["opportunity_id"]),
            security_id=str(payload["security_id"]),
            symbol=str(payload["symbol"]),
            observation_time=cls._parse_datetime(payload["observation_time"]),
            data_available_through=cls._parse_datetime(payload["data_available_through"]),
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
            next_known_event_time=cls._parse_datetime(payload.get("next_known_event_time")),
            catalyst_risk=str(payload["catalyst_risk"]),
            event_data_available_at=cls._parse_datetime(payload["event_data_available_at"]),
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
            primary_invalidation_price=float(payload["primary_invalidation_price"]),
            thesis_invalidation_reasons=tuple(payload.get("thesis_invalidation_reasons") or []),
            liquidity_risk=str(payload["liquidity_risk"]),
            gap_risk=str(payload["gap_risk"]),
            model_disagreement=bool(payload["model_disagreement"]),
            governance_eligible=bool(payload["governance_eligible"]),
            risk_eligible=bool(payload["risk_eligible"]),
            feature_values=dict(payload.get("feature_values") or {}),
            feature_versions=dict(payload.get("feature_versions") or {}),
            model_versions=dict(payload.get("model_versions") or {}),
            warehouse_manifest_hash=str(payload["warehouse_manifest_hash"]),
            dataset_manifest_hash=str(payload["dataset_manifest_hash"]),
            source_record_ids=tuple(payload.get("source_record_ids") or []),
            warnings=tuple(payload.get("warnings") or []),
            created_at=cls._parse_datetime(payload["created_at"]),
            schema_version=str(payload.get("schema_version", "1.0.0")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
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
