from __future__ import annotations

import argparse
import json

from alpha_velocity.audit import AuditLogger
from alpha_velocity.broker.ibkr import IBKRApp
from alpha_velocity.config import load_config
from alpha_velocity.research.report import run_research_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Velocity research-only IBKR run")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--symbols", default="JELD,HRTG,SM,GNSS,SPY")
    parser.add_argument("--output", default="research_reports")
    args = parser.parse_args()

    config = load_config(args.config)
    if config.broker.mode != "PAPER":
        raise SystemExit("Research launcher is restricted to broker.mode=PAPER.")
    if not config.execution.dry_run:
        raise SystemExit("Research launcher requires execution.dry_run=true.")

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    audit = AuditLogger(config.logging.audit_path)
    app = IBKRApp(config, audit)
    try:
        app.connect_and_start()
        report = run_research_report(app, symbols, args.output)
        audit.record("research_only_report_complete", report)
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        app.disconnect()


if __name__ == "__main__":
    main()
