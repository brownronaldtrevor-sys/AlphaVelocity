"""Alpha Lab main entry point for research and paper trading."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from alpha_velocity.alpha_lab import (
    AlphaLabEngine,
    SwingRepricingStrategy,
    generate_sample_alpha_lab_data,
    generate_sample_csv_data,
)
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse


def main() -> int:
    """Main CLI entry point for Alpha Lab."""
    parser = argparse.ArgumentParser(
        description="Alpha Lab - Strategy platform for research and paper trading",
        prog="alpha-lab",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # build-sample-data command
    build_parser = subparsers.add_parser(
        "build-sample-data",
        help="Build sample data in warehouse"
    )
    build_parser.add_argument(
        "--warehouse-path",
        default="./warehouse.db",
        help="Path to warehouse database"
    )

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run Alpha Lab and generate candidates"
    )
    run_parser.add_argument(
        "--strategy",
        choices=["all", "swing-repricing"],
        default="all",
        help="Strategy to run (all=swing-repricing only, turtle-trend is experimental)"
    )
    run_parser.add_argument(
        "--warehouse-path",
        default="./warehouse.db",
        help="Path to warehouse database"
    )
    run_parser.add_argument(
        "--output",
        default="./alpha_lab_results.json",
        help="Output file for candidates"
    )
    run_parser.add_argument(
        "--observation-time",
        help="Observation time ISO format (default: now)"
    )

    # generate-csv command
    csv_parser = subparsers.add_parser(
        "generate-csv",
        help="Generate sample CSV data"
    )
    csv_parser.add_argument(
        "--output-dir",
        default="./sample_data",
        help="Output directory for CSV files"
    )

    args = parser.parse_args()

    try:
        if args.command == "build-sample-data":
            return cmd_build_sample_data(args)
        elif args.command == "run":
            return cmd_run(args)
        elif args.command == "generate-csv":
            return cmd_generate_csv(args)
        else:
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_build_sample_data(args: argparse.Namespace) -> int:
    """Build sample data in warehouse."""
    print(f"Building sample Alpha Lab data...")
    print(f"  Warehouse: {args.warehouse_path}")

    try:
        eq_count, fut_count = generate_sample_alpha_lab_data(args.warehouse_path)
        print(f"✓ Added {eq_count} equities and {fut_count} futures")
        print(f"  Database: {args.warehouse_path}")
        return 0
    except Exception as e:
        print(f"✗ Failed to build sample data: {e}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run Alpha Lab and generate candidates."""
    # Determine observation time
    if args.observation_time:
        try:
            observation_time = datetime.fromisoformat(args.observation_time)
        except ValueError:
            print(f"Error: Invalid observation time format: {args.observation_time}", file=sys.stderr)
            return 1
    else:
        observation_time = datetime.now(timezone.utc)

    print(f"Running Alpha Lab...")
    print(f"  Warehouse: {args.warehouse_path}")
    print(f"  Strategy: {args.strategy}")
    print(f"  Observation time: {observation_time}")

    try:
        # Load warehouse
        if not Path(args.warehouse_path).exists():
            print(f"Error: Warehouse not found: {args.warehouse_path}", file=sys.stderr)
            print(f"  Try: python -m alpha_velocity.alpha_lab_main build-sample-data", file=sys.stderr)
            return 1

        warehouse = SQLiteHistoricalWarehouse(path=args.warehouse_path)

        # Create engine and register strategies
        engine = AlphaLabEngine()

        if args.strategy in ("all", "swing-repricing"):
            engine.register_strategy(SwingRepricingStrategy())

        # Run engine
        result = engine.run(
            warehouse=warehouse,
            observation_time=observation_time,
            universe_snapshot_id="alpha-lab-run",
            universe_size=None,
            dataset_manifest_hash="alpha-lab-sample",
            warehouse_manifest_hash="alpha-lab-sample",
        )

        # Output results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        output_data = {
            "run_id": result.run_id,
            "observation_time": result.observation_time.isoformat(),
            "unique_candidates": result.unique_candidates,
            "overlapping_symbols": result.overlapping_symbols,
            "strategies_run": result.strategies_run,
            "strategy_results": [
                {
                    "strategy_id": sr.strategy_id,
                    "strategy_name": sr.strategy_name,
                    "candidates_generated": sr.state.candidates_generated,
                    "triggered_count": sr.state.triggered_count,
                    "waiting_count": sr.state.waiting_count,
                    "excluded_count": sr.state.excluded_count,
                }
                for sr in result.strategy_results.values()
            ],
            "opportunities_count": len(result.opportunities),
            "opportunities": [
                {
                    "opportunity_id": opp.opportunity_id,
                    "symbol": opp.symbol,
                    "security_id": opp.security_id,
                    "setup_type": opp.setup_type,
                    "trigger_state": opp.trigger_state,
                    "breakout_distance_pct": opp.breakout_distance_pct,
                }
                for opp in (result.opportunities or [])
            ],
        }

        output_path.write_text(json.dumps(output_data, indent=2))

        print(f"✓ Generated {result.unique_candidates} unique candidates")
        print(f"  Strategies run: {len(result.strategy_results)}")
        for sr in result.strategy_results.values():
            print(f"    - {sr.strategy_name}: {sr.state.candidates_generated} candidates ({sr.state.triggered_count} triggered)")
        print(f"  Output: {output_path.absolute()}")
        return 0

    except Exception as e:
        print(f"✗ Failed to run Alpha Lab: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cmd_generate_csv(args: argparse.Namespace) -> int:
    """Generate sample CSV data."""
    print(f"Generating sample CSV data...")
    print(f"  Output directory: {args.output_dir}")

    try:
        file_count = generate_sample_csv_data(args.output_dir)
        print(f"✓ Generated {file_count} CSV files")
        print(f"  Directory: {Path(args.output_dir).absolute()}")
        return 0
    except Exception as e:
        print(f"✗ Failed to generate CSV data: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
