from __future__ import annotations

import argparse
import json
from pathlib import Path

from alpha_velocity.audit import AuditLogger
from alpha_velocity.broker.ibkr import IBKRApp
from alpha_velocity.config import load_config
from alpha_velocity.learning.journal import PredictionJournal
from alpha_velocity.paper_auto.executor import PaperExecutionController
from alpha_velocity.risk.engine import RiskEngine


def newest_json(folder: Path) -> Path:
    files = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No research JSON reports found in {folder}.")
    return files[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Velocity automatic IBKR paper trader")
    parser.add_argument("--config", default="config.paper.yaml")
    parser.add_argument("--research-folder", default="research_reports")
    args = parser.parse_args()

    config = load_config(args.config)
    audit = AuditLogger(config.logging.audit_path)
    report_path = newest_json(Path(args.research_folder))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    app = IBKRApp(config, audit)
    try:
        app.connect_and_start()
        controller = PaperExecutionController(
            app=app,
            risk=RiskEngine(config.risk),
            audit=audit,
            journal=PredictionJournal("learning_journal"),
        )
        result = controller.execute_from_report(report)
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        app.disconnect()


if __name__ == "__main__":
    main()
