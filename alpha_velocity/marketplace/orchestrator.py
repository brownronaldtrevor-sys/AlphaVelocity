"""Opportunity Marketplace Orchestrator - main engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.opportunity import Opportunity

from .classifier import MarketplaceClassifier
from .models import (
    MarketplaceQueue,
    MarketplaceResult,
    OpportunityCandidateClassification,
)


class OpportunityMarketplace:
    """Opportunity discovery, classification and research marketplace."""

    def __init__(self) -> None:
        """Initialize the marketplace."""
        self.classifier = MarketplaceClassifier()

    def organize(
        self,
        opportunities: list[Opportunity],
        observation_time: datetime | None = None,
    ) -> MarketplaceResult:
        """Organize opportunities into marketplace queues.

        Args:
            opportunities: List of Opportunity objects from ranking engine
            observation_time: Point-in-time reference

        Returns:
            MarketplaceResult with full classification and Top Five
        """
        if observation_time is None:
            if opportunities:
                observation_time = opportunities[0].observation_time
            else:
                observation_time = datetime.now(timezone.utc)

        run_id = f"MARKETPLACE-{observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        # Classify all opportunities
        classifications: list[OpportunityCandidateClassification] = []
        for opp in opportunities:
            classification = self.classifier.classify(opp, observation_time)
            classifications.append(classification)

        # Count by queue
        queue_counts: dict[str, int] = {}
        for queue in MarketplaceQueue:
            count = sum(1 for c in classifications if queue in c.marketplace_queues)
            if count > 0:
                queue_counts[queue.value] = count

        # Build the committee review funnel and Top Five from the same ordered shortlist
        committee_review_list = self._extract_committee_review_list(classifications)
        top_five = committee_review_list[:5]

        # Check if we're in fallback research mode
        fallback_research_mode = len([c for c in classifications if c.is_actionable]) == 0 and len(top_five) > 0

        # Count totals
        actionable_count = sum(1 for c in classifications if c.is_actionable)
        starter_count = sum(1 for c in classifications if MarketplaceQueue.STARTER_POSITION_CANDIDATE in c.marketplace_queues)
        near_trigger_count = sum(1 for c in classifications if MarketplaceQueue.NEAR_TRIGGER in c.marketplace_queues)
        research_count = sum(
            1
            for c in classifications
            if any(
                q in c.marketplace_queues
                for q in [
                    MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH,
                    MarketplaceQueue.CHART_MOMENTUM_RESEARCH,
                    MarketplaceQueue.TOP_DOWN_INDUSTRY_RESEARCH,
                    MarketplaceQueue.EVENT_ACTIVIST_RESEARCH,
                    MarketplaceQueue.SPECIAL_SITUATION,
                    MarketplaceQueue.RESEARCH_ONLY,
                    MarketplaceQueue.HIGH_RISK_SPECULATIVE,
                ]
            )
        )
        excluded_count = sum(1 for c in classifications if c.is_excluded)
        discovered_count = sum(1 for c in classifications if c.discovery_lenses or not c.is_excluded)

        # Warnings
        warnings: list[str] = []
        if len(classifications) == 0:
            warnings.append("No opportunities available for classification")
        if actionable_count == 0 and len(top_five) > 0:
            warnings.append("No immediately actionable candidates; Top Five populated with research opportunities")

        return MarketplaceResult(
            run_id=run_id,
            observation_time=observation_time,
            total_opportunities=len(classifications),
            actionable_count=actionable_count,
            starter_count=starter_count,
            near_trigger_count=near_trigger_count,
            research_count=research_count,
            excluded_count=excluded_count,
            discovered_count=discovered_count,
            queue_counts=queue_counts,
            candidate_classifications=tuple(classifications),
            committee_review_list=tuple(committee_review_list),
            top_five=tuple(top_five),
            warnings=tuple(warnings),
            fallback_research_mode=fallback_research_mode,
        )

    def _extract_committee_review_list(
        self,
        classifications: list[OpportunityCandidateClassification],
    ) -> list[OpportunityCandidateClassification]:
        """Extract the 10-candidate committee review list in priority order.

        Priority:
        1. ACTIONABLE_TRIGGERED (ranked by opportunity attractiveness)
        2. STARTER_POSITION_CANDIDATE
        3. NEAR_TRIGGER
        4. Highest-quality research candidates across independent queues
        """
        review_list: list[OpportunityCandidateClassification] = []

        # Priority 1: ACTIONABLE_TRIGGERED
        actionable = [
            c
            for c in classifications
            if MarketplaceQueue.ACTIONABLE_TRIGGERED in c.marketplace_queues
        ]
        actionable.sort(key=lambda x: x.opportunity_attractiveness, reverse=True)
        review_list.extend(actionable)

        if len(review_list) >= 10:
            return review_list[:10]

        # Priority 2: STARTER_POSITION_CANDIDATE
        starter = [
            c
            for c in classifications
            if MarketplaceQueue.STARTER_POSITION_CANDIDATE in c.marketplace_queues
            and c not in review_list
        ]
        starter.sort(key=lambda x: x.opportunity_attractiveness, reverse=True)
        review_list.extend(starter)

        if len(review_list) >= 10:
            return review_list[:10]

        # Priority 3: NEAR_TRIGGER
        near = [
            c for c in classifications if MarketplaceQueue.NEAR_TRIGGER in c.marketplace_queues and c not in review_list
        ]
        near.sort(key=lambda x: x.opportunity_attractiveness, reverse=True)
        review_list.extend(near)

        if len(review_list) >= 10:
            return review_list[:10]

        # Priority 4: Highest-quality research candidates
        research = [
            c
            for c in classifications
            if any(
                q in c.marketplace_queues
                for q in [
                    MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH,
                    MarketplaceQueue.CHART_MOMENTUM_RESEARCH,
                    MarketplaceQueue.TOP_DOWN_INDUSTRY_RESEARCH,
                    MarketplaceQueue.EVENT_ACTIVIST_RESEARCH,
                    MarketplaceQueue.SPECIAL_SITUATION,
                    MarketplaceQueue.RESEARCH_ONLY,
                ]
            )
            and c not in review_list
        ]
        research.sort(key=lambda x: (x.research_confidence, x.opportunity_attractiveness), reverse=True)
        review_list.extend(research)

        return review_list[:10]

    def get_queue(
        self,
        marketplace_result: MarketplaceResult,
        queue: MarketplaceQueue,
    ) -> list[OpportunityCandidateClassification]:
        """Get all candidates in a specific queue."""
        return [c for c in marketplace_result.candidate_classifications if queue in c.marketplace_queues]

    def get_all_queues(
        self,
        marketplace_result: MarketplaceResult,
    ) -> dict[str, list[OpportunityCandidateClassification]]:
        """Get all candidates organized by queue."""
        result: dict[str, list[OpportunityCandidateClassification]] = {}
        for queue in MarketplaceQueue:
            queue_candidates = self.get_queue(marketplace_result, queue)
            if queue_candidates:
                result[queue.value] = queue_candidates
        return result

    def to_dict(self, marketplace_result: MarketplaceResult) -> dict[str, Any]:
        """Convert marketplace result to dictionary."""
        return {
            "run_id": marketplace_result.run_id,
            "observation_time": marketplace_result.observation_time.isoformat(),
            "total_opportunities": marketplace_result.total_opportunities,
            "actionable_count": marketplace_result.actionable_count,
            "starter_count": marketplace_result.starter_count,
            "near_trigger_count": marketplace_result.near_trigger_count,
            "research_count": marketplace_result.research_count,
            "excluded_count": marketplace_result.excluded_count,
            "queue_counts": marketplace_result.queue_counts,
            "top_five_count": len(marketplace_result.top_five),
            "top_five": [
                {
                    "symbol": c.symbol,
                    "queues": [q.value for q in c.marketplace_queues],
                    "attractiveness": c.opportunity_attractiveness,
                    "research_confidence": c.research_confidence,
                }
                for c in marketplace_result.top_five
            ],
            "fallback_research_mode": marketplace_result.fallback_research_mode,
            "warnings": marketplace_result.warnings,
        }
