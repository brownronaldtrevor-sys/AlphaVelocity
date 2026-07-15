from __future__ import annotations

from alpha_velocity.models import SignalProposal


class OpportunityAllocator:
    """Ranks proposals before they are sent to independent risk controls."""

    @staticmethod
    def rank(proposals: list[SignalProposal]) -> list[SignalProposal]:
        return sorted(
            proposals,
            key=lambda p: (
                p.alpha_velocity,
                p.probability_target_before_stop,
                p.reward_to_risk,
            ),
            reverse=True,
        )
