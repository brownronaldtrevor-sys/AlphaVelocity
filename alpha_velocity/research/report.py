from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from alpha_velocity.broker.contracts import to_ib_contract
from alpha_velocity.models import AssetClass, Instrument
from alpha_velocity.broker.ibkr import IBKRApp
from alpha_velocity.shadow.cio import ShadowCIO
from alpha_velocity.shadow.models import DecisionCandidate
from alpha_velocity.signals.technical import compute_snapshot


def _candidate(symbol: str, snapshot) -> DecisionCandidate:
    # These are explicitly non-predictive research mappings. They make the existing
    # Shadow CIO/reporting interfaces usable without pretending that heuristic scores
    # are calibrated probabilities.
    readiness = float(snapshot.composite_score)
    return DecisionCandidate(
        opportunity_id=symbol,
        proposed_action="RESEARCH",
        current_weight_pct=0.0,
        proposed_weight_pct=0.0,
        opportunity_score=readiness / 100.0,
        readiness_score=readiness,
        expected_return_pct=0.0,
        expected_holding_days=0.0,
        downside_pct=0.0,
        uncertainty=85.0,
        liquidity_score=min(95.0, 35.0 + snapshot.volume_ratio_20d * 20.0),
        execution_quality=50.0,
        thesis_strength=0.0,
        technical_strength=readiness,
        macro_strength=0.0,
        evidence_count=1,
        contradiction_count=0,
        model_disagreement=50.0,
        data_trust_score=75.0,
        notes=[
            "Research-only technical snapshot.",
            "Expected-return fields intentionally unset until calibrated models exist.",
        ],
    )


def run_research_report(
    app: IBKRApp,
    symbols: list[str],
    output_folder: str,
) -> dict:
    snapshots = {}
    failures = {}
    req_id = 12000

    for symbol in symbols:
        req_id += 1
        try:
            contract = to_ib_contract(Instrument(symbol=symbol, asset_class=AssetClass.STOCK))
            bars = app.request_daily_bars(req_id, contract)
            snapshots[symbol] = compute_snapshot(bars)
        except Exception as exc:  # each symbol fails independently
            failures[symbol] = f"{type(exc).__name__}: {exc}"

    candidates = [_candidate(symbol, snap) for symbol, snap in snapshots.items()]
    shadow_verdicts = ShadowCIO().review(candidates) if len(candidates) >= 1 else []

    ranked = sorted(
        snapshots.items(),
        key=lambda item: item[1].composite_score,
        reverse=True,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "RESEARCH_ONLY",
        "orders_submitted": 0,
        "symbols_requested": symbols,
        "symbols_completed": list(snapshots),
        "failures": failures,
        "technical_rank": [
            {
                "rank": idx,
                "symbol": symbol,
                "state": snap.state,
                "technical_composite": snap.composite_score,
                "trend_score": snap.trend_score,
                "breakout_score": snap.breakout_score,
                "volume_score": snap.volume_score,
                "reversal_score": snap.reversal_score,
                "close": snap.close,
                "return_5d": snap.return_5d,
                "return_20d": snap.return_20d,
                "volume_ratio_20d": snap.volume_ratio_20d,
                "atr_pct_14d": snap.atr_pct_14d,
            }
            for idx, (symbol, snap) in enumerate(ranked, start=1)
        ],
        "shadow_review": [asdict(v) for v in shadow_verdicts],
        "critical_disclaimer": (
            "The technical scores are transparent heuristics, not calibrated forecasts. "
            "This report generates research observations only and has no order path."
        ),
    }
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report["report_path"] = str(path.resolve())
    return report
