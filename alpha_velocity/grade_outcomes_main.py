from __future__ import annotations

import json

from alpha_velocity.audit import AuditLogger
from alpha_velocity.broker.ibkr import IBKRApp
from alpha_velocity.config import load_config
from alpha_velocity.learning.ibkr_grader import IBKROutcomeGrader
from alpha_velocity.learning.journal import PredictionJournal


def main() -> None:
    config = load_config("config.yaml")
    if config.broker.mode != "PAPER" or not config.execution.dry_run:
        raise SystemExit("Outcome grading requires the safe research config.")
    audit = AuditLogger(config.logging.audit_path)
    app = IBKRApp(config, audit)
    try:
        app.connect_and_start()
        records = IBKROutcomeGrader(
            app,
            PredictionJournal("learning_journal"),
        ).grade_pending()
        print(json.dumps([r.__dict__ for r in records], indent=2))
    finally:
        app.disconnect()


if __name__ == "__main__":
    main()
