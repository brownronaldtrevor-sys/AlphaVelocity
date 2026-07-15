from __future__ import annotations

import argparse
import json

from alpha_velocity.audit import AuditLogger
from alpha_velocity.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project Alpha Velocity institutional connection/audit utility"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--connect",
        action="store_true",
        help="Connect to TWS/IB Gateway and read state. Never submits demo orders.",
    )
    parser.add_argument(
        "--offline-demo",
        action="store_true",
        help="Run the synthetic risk-wiring demonstration without a broker connection.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.connect and args.offline_demo:
        raise SystemExit("Choose either --connect or --offline-demo, not both.")

    config = load_config(args.config)
    audit = AuditLogger(config.logging.audit_path)

    if args.connect:
        from alpha_velocity.broker.ibkr import IBKRApp

        app = IBKRApp(config, audit)
        try:
            app.connect_and_start()
            snapshot = app.require_account_snapshot()
            result = {
                "connected": True,
                "mode": config.broker.mode,
                "dry_run": config.execution.dry_run,
                "account_snapshot": snapshot,
                "positions": app.positions,
                "open_order_count": len(app.open_order_ids),
                "open_orders_snapshot_complete": app.open_orders_complete.is_set(),
                "orders_submitted": 0,
                "message": "Connection test only. Synthetic strategies are never transmitted.",
            }
            audit.record("connection_test_complete", result)
            print(json.dumps(result, indent=2, sort_keys=True))
        finally:
            app.disconnect()
        return

    if args.offline_demo:
        from alpha_velocity.models import AccountState
        from alpha_velocity.portfolio.allocator import OpportunityAllocator
        from alpha_velocity.risk.engine import RiskEngine
        from alpha_velocity.strategies.demo import DemonstrationStrategy

        risk = RiskEngine(config.risk)
        account = AccountState(
            net_liquidation=config.risk.starting_equity_fallback,
            available_funds=config.risk.starting_equity_fallback,
            gross_position_value=0.0,
            daily_pnl=0.0,
            open_orders=0,
        )
        proposal = OpportunityAllocator.rank(DemonstrationStrategy().generate())[0]
        decision = risk.evaluate(proposal, account, positions=[])
        output = {
            "offline_demo": True,
            "approved_by_risk_wiring": decision.is_approved,
            "orders_submitted": 0,
            "warning": "Synthetic wiring test only; not an investment model.",
        }
        audit.record("offline_wiring_test", output)
        print(json.dumps(output, indent=2))
        return

    raise SystemExit("Specify --connect or --offline-demo.")


if __name__ == "__main__":
    main()
