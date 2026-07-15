from __future__ import annotations
import argparse, json
from alpha_velocity.paper.daily_pipeline import DailyPaperPipeline

def main():
    parser = argparse.ArgumentParser(description="Alpha Velocity v0.4 paper pipeline")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--data-folder", required=True)
    parser.add_argument("--state", default="./paper_state/account.json")
    parser.add_argument("--reports", default="./paper_reports")
    parser.add_argument("--starting-cash", type=float, default=100000)
    args = parser.parse_args()

    pipeline = DailyPaperPipeline(
        symbols=[s.strip().upper() for s in args.symbols.split(",") if s.strip()],
        data_folder=args.data_folder,
        state_path=args.state,
        report_folder=args.reports,
        starting_cash=args.starting_cash,
    )
    print(json.dumps(pipeline.run(), indent=2))

if __name__ == "__main__":
    main()
