"""Alpha Lab strategy protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import (
        CandidateState,
        StrategyCandidate,
        StrategyContext,
        StrategyRunResult,
        StrategyValidationStatus,
    )


class StrategyProtocol(ABC):
    """Abstract protocol for Alpha Lab strategies."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique strategy identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable strategy name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def strategy_version(self) -> str:
        """Strategy version (e.g. '1.0.0')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_asset_types(self) -> tuple[str, ...]:
        """Asset types this strategy supports (e.g. ('STOCK', 'FUTURE'))."""
        raise NotImplementedError

    @property
    @abstractmethod
    def required_history(self) -> int:
        """Minimum bars of history required (e.g. 365 days)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def required_data(self) -> tuple[str, ...]:
        """Data fields required (e.g. ('OHLCV', 'INDICATORS'))."""
        raise NotImplementedError

    @property
    @abstractmethod
    def hypothesis(self) -> str:
        """Clear statement of the strategy hypothesis."""
        raise NotImplementedError

    @property
    @abstractmethod
    def validation_status(self) -> StrategyValidationStatus:
        """Current validation status."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ranking_influence(self) -> float:
        """Influence weight on ranking (0.0 if UNCALIBRATED)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def allocation_influence(self) -> float:
        """Influence weight on allocation (0.0 if UNCALIBRATED)."""
        raise NotImplementedError

    @abstractmethod
    def generate_candidates(self, context: StrategyContext) -> StrategyRunResult:
        """Generate candidates for the given context.

        Args:
            context: Strategy execution context with warehouse and config

        Returns:
            StrategyRunResult containing candidates and metadata

        Constraints:
            - Must use only point-in-time data (data_available_through <= observation_time)
            - Must not create orders
            - Must not mutate warehouse or portfolio
            - Must not call brokers
            - Must retain evidence lineage
            - Must support deterministic serialization
        """
        raise NotImplementedError

    @abstractmethod
    def explain_candidate(self, candidate_id: str) -> str:
        """Provide detailed explanation of a candidate.

        Args:
            candidate_id: The candidate to explain

        Returns:
            Human-readable explanation of the thesis
        """
        raise NotImplementedError
