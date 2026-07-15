from __future__ import annotations

import argparse
import json
from pathlib import Path

from alpha_velocity.paper_auto.controller import PaperLearningController


def newest_json(folder: Path) -> Path:
    files = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No JSON reports found in {folder}")
    return files[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Alpha Velocity paper order plan")
    parser.add_argument("--research-folder", default="research_reports")
    parser.add_argument("--equity", type=float, default=100000.0)
    args = parser.parse_args()

    report_path = newest_json(Path(args.research_folder))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    controller = PaperLearningController()
    plan = controller.build_plan(
        research_report=report,
        account_equity=args.equity,
        current_positions={},
    )
    print(json.dumps(plan, indent=2, default=str))


if __name__ == "__main__":
    main()
