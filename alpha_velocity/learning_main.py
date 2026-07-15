from __future__ import annotations

import json

from alpha_velocity.learning.journal import PredictionJournal
from alpha_velocity.learning.scorecard import ChallengerPromotionGate


def main() -> None:
    journal = PredictionJournal("learning_journal")
    forecasts = journal.load_forecasts()
    outcomes = journal.load_outcomes()
    scorecards = ChallengerPromotionGate().build_scorecards(forecasts, outcomes)

    print(json.dumps(
        [s.__dict__ for s in scorecards],
        indent=2,
        default=str,
    ))


if __name__ == "__main__":
    main()
