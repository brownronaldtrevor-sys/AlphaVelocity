from __future__ import annotations

from abc import ABC, abstractmethod

from alpha_velocity.models import SignalProposal


class Strategy(ABC):
    strategy_id: str

    @abstractmethod
    def generate(self) -> list[SignalProposal]:
        raise NotImplementedError
