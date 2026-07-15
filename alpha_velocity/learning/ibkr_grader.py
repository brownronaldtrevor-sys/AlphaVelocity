from __future__ import annotations

from datetime import datetime, timezone

from alpha_velocity.broker.contracts import to_ib_contract
from alpha_velocity.learning.journal import PredictionJournal
from alpha_velocity.learning.models import OutcomeRecord
from alpha_velocity.models import AssetClass, Instrument


class IBKROutcomeGrader:
    def __init__(self, app, journal: PredictionJournal) -> None:
        self.app = app
        self.journal = journal

    def grade_pending(self) -> list[OutcomeRecord]:
        forecasts = self.journal.load_forecasts()
        outcomes = self.journal.load_outcomes()
        completed = {o["forecast_id"] for o in outcomes}
        records: list[OutcomeRecord] = []
        req_id = 40000

        for forecast in forecasts:
            if forecast["forecast_id"] in completed:
                continue
            req_id += 1
            contract = to_ib_contract(
                Instrument(symbol=forecast["symbol"], asset_class=AssetClass.STOCK)
            )
            bars = self.app.request_daily_bars(req_id, contract, duration="1 Y")
            decision_date = datetime.fromisoformat(
                forecast["decision_time"].replace("Z", "+00:00")
            ).date()
            eligible = [bar for bar in bars if bar.timestamp.date() > decision_date]
            if not eligible:
                continue

            entry = float(forecast["feature_snapshot"]["entry_price"])
            target = float(forecast["feature_snapshot"]["target_price"])
            stop = float(forecast["feature_snapshot"]["stop_price"])
            horizon = int(forecast["horizon_days"])
            observed = eligible[:horizon]

            target_hit = False
            stop_hit = False
            target_before_stop = None
            ambiguous = False

            for bar in observed:
                hit_t = bar.high >= target
                hit_s = bar.low <= stop
                if hit_t and hit_s:
                    target_hit = True
                    stop_hit = True
                    ambiguous = True
                    break
                if hit_t:
                    target_hit = True
                    target_before_stop = True
                    break
                if hit_s:
                    stop_hit = True
                    target_before_stop = False
                    break

            is_complete = target_hit or stop_hit or len(observed) >= horizon
            if not is_complete:
                continue

            last_close = observed[-1].close
            highs = [bar.high for bar in observed]
            lows = [bar.low for bar in observed]
            record = OutcomeRecord(
                forecast_id=forecast["forecast_id"],
                symbol=forecast["symbol"],
                evaluation_time=datetime.now(timezone.utc).isoformat(),
                realized_return_pct=(last_close / entry - 1.0) * 100.0,
                target_hit=target_hit,
                stop_hit=stop_hit,
                target_before_stop=None if ambiguous else target_before_stop,
                maximum_favorable_excursion_pct=(max(highs) / entry - 1.0) * 100.0,
                maximum_adverse_excursion_pct=(min(lows) / entry - 1.0) * 100.0,
                bars_observed=len(observed),
            )
            self.journal.append_outcome(record)
            records.append(record)
        return records
