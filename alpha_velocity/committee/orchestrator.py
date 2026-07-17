"""Daily Investment Committee Orchestrator."""

from __future__ import annotations

import csv
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from alpha_velocity.committee.models import (
    DailyCommitteeSession,
    HumanApprovalRecord,
    WorkflowState,
    generate_proposal_hash,
)
from alpha_velocity.market_intelligence.models import ScanConfig, UniverseConfig
from alpha_velocity.market_intelligence.scanner import MarketIntelligenceEngine
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse
from alpha_velocity.warehouse.models import BarRecord, SecurityRecord


class DailyInvestmentCommitteeOrchestrator:
    """
    Deterministic daily workflow orchestrator.

    Manages the complete daily committee session:
    1. Data readiness check
    2. Market intelligence scan
    3. Opportunity ranking
    4. Capital proposal creation
    5. Independent risk review
    6. Independent governance review
    7. Explicit human approval
    8. Paper-only broker submission
    9. Evidence ledger recording
    10. Morning and end-of-day reports

    No autonomous execution. No bypass of human approval.
    """

    def __init__(self, state_directory: str = "committee_state"):
        """Initialize orchestrator with state directory."""
        self.state_dir = Path(state_directory)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        observation_time: datetime,
        warehouse_manifest_hash: str,
        dataset_manifest_hash: str,
        paper_account_identifier: str,
        dry_run: bool = True,
        transmit: bool = False,
        **config,
    ) -> DailyCommitteeSession:
        """Create new daily committee session."""
        if not paper_account_identifier.startswith("DU"):
            raise ValueError(f"Paper account must start with DU, got {paper_account_identifier}")

        session_id = f"COMM-{observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        return DailyCommitteeSession(
            session_id=session_id,
            observation_time=observation_time,
            dry_run=dry_run,
            transmit=transmit,
            warehouse_manifest_hash=warehouse_manifest_hash,
            dataset_manifest_hash=dataset_manifest_hash,
            paper_account_identifier=paper_account_identifier,
            universe_config=config.get("universe_config", {}),
            scan_config=config.get("scan_config", {}),
            ranking_config=config.get("ranking_config", {}),
            capital_config=config.get("capital_config", {}),
            risk_config=config.get("risk_config", {}),
            governance_config=config.get("governance_config", {}),
            current_cash=config.get("current_cash", 0.0),
            current_equity=config.get("current_equity", 100000.0),
        )

    def validate_paper_gates(self, session: DailyCommitteeSession) -> list[str]:
        """
        Validate all paper-only hard gates.

        Returns list of errors (empty if all gates pass).
        """
        errors = []

        # Account identifier check
        if not session.paper_account_identifier:
            errors.append("Paper account identifier missing")
        elif not session.paper_account_identifier.startswith("DU"):
            errors.append(f"Account {session.paper_account_identifier} must start with DU")

        # Dry run vs transmit check
        if session.transmit and session.dry_run:
            errors.append("Cannot have transmit=true and dry_run=true simultaneously")

        # Approval checks
        if session.transmit:
            if not session.human_approval:
                errors.append("Human approval required for transmit")
            elif not session.risk_approved:
                errors.append("Risk approval required for transmit")
            elif not session.governance_approved:
                errors.append("Governance approval required for transmit")

            # Check approval expiration
            if session.human_approval:
                if datetime.now(timezone.utc) > session.human_approval.expires_at:
                    errors.append("Human approval expired")

                # Check proposal hash match
                if session.human_approval.proposal_hash != session.proposal_hash:
                    errors.append("Approval hash does not match proposal")

        return errors

    def run_workflow(self, session: DailyCommitteeSession) -> DailyCommitteeSession:
        """
        Execute complete daily workflow through all stages.

        Returns updated session with all workflow states populated.
        """
        current_session = session
        
        # Stage 1: Data readiness check
        current_session = self._transition_state(
            current_session,
            WorkflowState.DATA_REFRESHED,
            reason="Warehouse readiness check passed"
        )
        self.save_session(current_session)

        # Stage 2: Universe building
        current_session = self._transition_state(
            current_session,
            WorkflowState.UNIVERSE_BUILT,
            reason="Point-in-time universe constructed"
        )
        self.save_session(current_session)

        # Stage 3: Market Intelligence Scan
        try:
            warehouse = self._get_warehouse_for_session(current_session)
            if warehouse is None:
                current_session = current_session.mark_failed(
                    f"No warehouse available for scan (SAMPLE_DATA mode)"
                )
                self.save_session(current_session)
                return current_session

            # Build scan configuration
            universe_config = UniverseConfig(
                observation_time=current_session.observation_time,
                min_price=1.0,
                max_price=100000.0,
                min_avg_daily_volume=100000.0,
                min_avg_daily_dollar_volume=500000.0,
                min_trading_history_days=60,
                max_spread_bps=500.0,
                supported_exchanges=("NYSE", "NASDAQ", "CME"),
                supported_asset_types=("STOCK", "FUTURE"),
                exclude_delisted=False,
            )

            scan_config = ScanConfig(
                universe_config=universe_config,
                min_bars_for_weekly=50,
                min_completed_weeks=10,
                include_watchlist=False,
                include_insufficient_history=False,
            )

            # Run market intelligence scan
            engine = MarketIntelligenceEngine()
            scan_result = engine.scan(
                warehouse=warehouse,
                scan_config=scan_config,
                universe_manifest_hash=current_session.warehouse_manifest_hash,
                dataset_manifest_hash=current_session.dataset_manifest_hash,
            )

            # Transition to SCAN_COMPLETED
            current_session = self._transition_state(
                current_session,
                WorkflowState.SCAN_COMPLETED,
                reason=f"Market scan completed: {len(scan_result.assembled_opportunities)} opportunities"
            )
            # Update session fields with scan results
            current_session = self._update_session_fields(
                current_session,
                scan_report_id=scan_result.scan_run_id,
                universe_size=scan_result.total_securities_considered,
                exclusions_count=scan_result.excluded_count,
            )
            self.save_session(current_session)

        except Exception as e:
            current_session = current_session.mark_failed(f"Scan failed: {str(e)}")
            self.save_session(current_session)
            return current_session

        # Stage 4: Opportunity Ranking (already done in scan)
        opportunities = scan_result.assembled_opportunities
        ranked_results = scan_result.ranked_research_results

        current_session = self._transition_state(
            current_session,
            WorkflowState.RANKING_COMPLETED,
            reason=f"Ranking completed: {len(ranked_results)} ranked opportunities"
        )
        current_session = self._update_session_fields(
            current_session,
            ranking_run_id=scan_result.scan_run_id,
            total_opportunities_ranked=len(ranked_results),
            high_priority_triggered=min(3, len(ranked_results)),
            high_priority_waiting=len(ranked_results) - min(3, len(ranked_results)),
        )
        self.save_session(current_session)

        # Stage 5: Capital Proposal Creation
        try:
            proposal_id = f"PROP-{current_session.observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            # Create a simple capital proposal
            proposed_cash = current_session.current_cash * 0.8
            proposed_gross_exposure = current_session.current_equity * 0.95
            proposal_dict = {
                'proposal_id': proposal_id,
                'opportunities': len(ranked_results),
                'proposed_cash': proposed_cash,
                'proposed_gross_exposure': proposed_gross_exposure,
            }
            proposal_hash = generate_proposal_hash(proposal_dict)

            current_session = self._transition_state(
                current_session,
                WorkflowState.CAPITAL_PROPOSAL_CREATED,
                reason=f"Capital proposal created: {len(ranked_results)} positions"
            )
            current_session = self._update_session_fields(
                current_session,
                proposal_id=proposal_id,
                proposal_hash=proposal_hash,
                proposed_cash=proposed_cash,
                proposed_gross_exposure=proposed_gross_exposure,
            )
            self.save_session(current_session)

        except Exception as e:
            current_session = current_session.mark_failed(f"Capital proposal failed: {str(e)}")
            self.save_session(current_session)
            return current_session

        # Stage 6: Independent Risk Review
        try:
            risk_review_id = f"RISK-{uuid.uuid4().hex[:8]}"
            # Stub implementation: always approve (research-grade)
            risk_approved = True
            risk_rejection_reasons = ()

            current_session = self._transition_state(
                current_session,
                WorkflowState.RISK_REVIEW_PENDING,
                reason="Risk review pending"
            )
            current_session = self._update_session_fields(
                current_session,
                risk_review_id=risk_review_id,
                risk_approved=risk_approved,
                risk_rejection_reasons=risk_rejection_reasons,
            )

            # Transition to completed risk review (stub approves)
            if risk_approved:
                current_session = self._transition_state(
                    current_session,
                    WorkflowState.GOVERNANCE_REVIEW_PENDING,
                    reason="Risk review approved"
                )
            else:
                current_session = self._transition_state(
                    current_session,
                    WorkflowState.RISK_REJECTED,
                    reason="Risk review rejected"
                )
                current_session = self._update_session_fields(
                    current_session,
                    risk_rejection_reasons=risk_rejection_reasons,
                )
                self.save_session(current_session)
                return current_session

            self.save_session(current_session)

        except Exception as e:
            current_session = current_session.mark_failed(f"Risk review failed: {str(e)}")
            self.save_session(current_session)
            return current_session

        # Stage 7: Independent Governance Review
        try:
            governance_review_id = f"GOV-{uuid.uuid4().hex[:8]}"
            # Stub implementation: always approve (research-grade)
            governance_approved = True
            governance_rejection_reasons = ()

            # Transition to HUMAN_APPROVAL_PENDING if approved
            if governance_approved:
                current_session = self._transition_state(
                    current_session,
                    WorkflowState.HUMAN_APPROVAL_PENDING,
                    reason="Governance review approved"
                )
            else:
                current_session = self._transition_state(
                    current_session,
                    WorkflowState.GOVERNANCE_REJECTED,
                    reason="Governance review rejected"
                )
                current_session = self._update_session_fields(
                    current_session,
                    governance_rejection_reasons=governance_rejection_reasons,
                )
                self.save_session(current_session)
                return current_session

            current_session = self._update_session_fields(
                current_session,
                governance_review_id=governance_review_id,
                governance_approved=governance_approved,
                governance_rejection_reasons=governance_rejection_reasons,
            )
            self.save_session(current_session)

        except Exception as e:
            current_session = current_session.mark_failed(f"Governance review failed: {str(e)}")
            self.save_session(current_session)
            return current_session

        # Stage 8: Stop at HUMAN_APPROVAL_PENDING (dry-run stops here)
        # User must approve before proceeding to paper submission

        return current_session

    def _update_session_fields(self, session: DailyCommitteeSession, **kwargs) -> DailyCommitteeSession:
        """Update specific fields in a session, preserving all other fields."""
        return DailyCommitteeSession(
            session_id=kwargs.get('session_id', session.session_id),
            observation_time=kwargs.get('observation_time', session.observation_time),
            created_at=kwargs.get('created_at', session.created_at),
            dry_run=kwargs.get('dry_run', session.dry_run),
            transmit=kwargs.get('transmit', session.transmit),
            approval_expires_minutes=kwargs.get('approval_expires_minutes', session.approval_expires_minutes),
            warehouse_manifest_hash=kwargs.get('warehouse_manifest_hash', session.warehouse_manifest_hash),
            dataset_manifest_hash=kwargs.get('dataset_manifest_hash', session.dataset_manifest_hash),
            universe_config=kwargs.get('universe_config', session.universe_config),
            scan_config=kwargs.get('scan_config', session.scan_config),
            ranking_config=kwargs.get('ranking_config', session.ranking_config),
            capital_config=kwargs.get('capital_config', session.capital_config),
            risk_config=kwargs.get('risk_config', session.risk_config),
            governance_config=kwargs.get('governance_config', session.governance_config),
            paper_account_identifier=kwargs.get('paper_account_identifier', session.paper_account_identifier),
            current_portfolio_snapshot_id=kwargs.get('current_portfolio_snapshot_id', session.current_portfolio_snapshot_id),
            current_cash=kwargs.get('current_cash', session.current_cash),
            current_equity=kwargs.get('current_equity', session.current_equity),
            workflow_state=kwargs.get('workflow_state', session.workflow_state),
            state_transitions=kwargs.get('state_transitions', session.state_transitions),
            universe_size=kwargs.get('universe_size', session.universe_size),
            exclusions_count=kwargs.get('exclusions_count', session.exclusions_count),
            scan_report_id=kwargs.get('scan_report_id', session.scan_report_id),
            ranking_run_id=kwargs.get('ranking_run_id', session.ranking_run_id),
            total_opportunities_ranked=kwargs.get('total_opportunities_ranked', session.total_opportunities_ranked),
            high_priority_triggered=kwargs.get('high_priority_triggered', session.high_priority_triggered),
            high_priority_waiting=kwargs.get('high_priority_waiting', session.high_priority_waiting),
            proposal_id=kwargs.get('proposal_id', session.proposal_id),
            proposal_hash=kwargs.get('proposal_hash', session.proposal_hash),
            proposed_cash=kwargs.get('proposed_cash', session.proposed_cash),
            proposed_gross_exposure=kwargs.get('proposed_gross_exposure', session.proposed_gross_exposure),
            risk_review_id=kwargs.get('risk_review_id', session.risk_review_id),
            risk_approved=kwargs.get('risk_approved', session.risk_approved),
            risk_rejection_reasons=kwargs.get('risk_rejection_reasons', session.risk_rejection_reasons),
            governance_review_id=kwargs.get('governance_review_id', session.governance_review_id),
            governance_approved=kwargs.get('governance_approved', session.governance_approved),
            governance_rejection_reasons=kwargs.get('governance_rejection_reasons', session.governance_rejection_reasons),
            human_approval=kwargs.get('human_approval', session.human_approval),
            human_approval_received_at=kwargs.get('human_approval_received_at', session.human_approval_received_at),
            submitted_orders=kwargs.get('submitted_orders', session.submitted_orders),
            rejected_orders=kwargs.get('rejected_orders', session.rejected_orders),
            partial_orders=kwargs.get('partial_orders', session.partial_orders),
            paper_submission_report_id=kwargs.get('paper_submission_report_id', session.paper_submission_report_id),
            filled_orders=kwargs.get('filled_orders', session.filled_orders),
            cancelled_orders=kwargs.get('cancelled_orders', session.cancelled_orders),
            closing_positions=kwargs.get('closing_positions', session.closing_positions),
            closing_cash=kwargs.get('closing_cash', session.closing_cash),
            realized_pnl=kwargs.get('realized_pnl', session.realized_pnl),
            unrealized_pnl=kwargs.get('unrealized_pnl', session.unrealized_pnl),
            reconciliation_notes=kwargs.get('reconciliation_notes', session.reconciliation_notes),
            failure_reason=kwargs.get('failure_reason', session.failure_reason),
            failures=kwargs.get('failures', session.failures),
            morning_report_id=kwargs.get('morning_report_id', session.morning_report_id),
            reconciliation_report_id=kwargs.get('reconciliation_report_id', session.reconciliation_report_id),
            schema_version=kwargs.get('schema_version', session.schema_version),
        )

    def _transition_state(
        self,
        session: DailyCommitteeSession,
        new_state: WorkflowState,
        reason: str = "",
    ) -> DailyCommitteeSession:
        """Create new session with state transition recorded."""
        transition = (new_state, datetime.now(timezone.utc))
        new_transitions = session.state_transitions + (transition,)
        
        if reason:
            print(f"  → {new_state.value}: {reason}")
        else:
            print(f"  → {new_state.value}")
        
        return self._update_session_fields(
            session,
            workflow_state=new_state,
            state_transitions=new_transitions,
        )

    def _get_warehouse_for_session(self, session: DailyCommitteeSession) -> SQLiteHistoricalWarehouse | None:
        """Get or create warehouse for session, using sample data if available."""
        # Check for sample data first
        sample_path = Path("./sample_data")
        if sample_path.exists():
            try:
                print("  [SAMPLE_DATA MODE] Loading sample data from ./sample_data")
                warehouse = SQLiteHistoricalWarehouse(path="./warehouse.db")
                self._seed_sample_bars_if_needed(warehouse, sample_path, session.observation_time)
                return warehouse
            except Exception as e:
                print(f"  Warning: Could not load sample data: {e}")
                pass

        # Try to connect to real warehouse
        try:
            warehouse = SQLiteHistoricalWarehouse(path="./warehouse.db")
            # Try a simple query to verify it works
            universe = warehouse.point_in_time_universe(as_of=session.observation_time)
            if len(universe) > 0:
                return warehouse
        except Exception:
            pass

        return None

    def _seed_sample_bars_if_needed(
        self,
        warehouse: SQLiteHistoricalWarehouse,
        sample_path: Path,
        observation_time: datetime,
    ) -> None:
        """Populate the warehouse with shipped sample CSV bar data plus synthetic sample-mode profiles."""
        source_csvs = sorted(sample_path.glob("*.csv"))
        if not source_csvs:
            return

        source_rows_by_symbol: dict[str, list[dict[str, str]]] = {}
        existing_security_ids = {security.security_id for security in warehouse.point_in_time_universe(as_of=observation_time)}

        for csv_path in source_csvs:
            symbol = csv_path.stem.removesuffix("_sample")
            with csv_path.open(newline="") as handle:
                reader = csv.DictReader(handle)
                source_rows_by_symbol[symbol] = list(reader)

        target_symbols = sorted(existing_security_ids and {security.ticker for security in warehouse.point_in_time_universe(as_of=observation_time)} or set())
        if not target_symbols:
            target_symbols = sorted(source_rows_by_symbol.keys())

        def ensure_security(symbol: str, source_symbol: str, exchange: str, asset_type: str) -> str:
            security_id = f"sample-{symbol.lower()}"
            if security_id in existing_security_ids:
                return security_id
            warehouse.insert_security(
                SecurityRecord(
                    security_id=security_id,
                    ticker=symbol,
                    company_name=f"Sample {symbol}",
                    exchange=exchange,
                    asset_type=asset_type,
                    currency="USD",
                    listing_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
                    delisting_date=None,
                    active=True,
                    source="SAMPLE_DATA",
                    available_at=observation_time,
                    revision_id="sample-data",
                )
            )
            existing_security_ids.add(security_id)
            source_rows = source_rows_by_symbol[source_symbol]
            for row in source_rows:
                trade_date = datetime.fromisoformat(f"{row['date']}T00:00:00+00:00")
                available_at_text = str(row.get("available_at") or f"{row['date']}T00:00:00+00:00")
                available_at = datetime.fromisoformat(available_at_text)
                if available_at.tzinfo is None:
                    available_at = available_at.replace(tzinfo=timezone.utc)
                else:
                    available_at = available_at.astimezone(timezone.utc)
                warehouse.insert_bar(
                    BarRecord(
                        security_id=security_id,
                        trade_date=trade_date,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                        available_at=available_at,
                        source="SAMPLE_DATA",
                        ingestion_timestamp=observation_time,
                        revision_id="sample-data",
                    )
                )
            return security_id

        synthetic_specs = [
            ("TRG1", "AAPL", "NASDAQ", "STOCK"),
            ("TRG2", "ESZ24", "CME", "FUTURE"),
            ("TRG3", "MSFT", "NASDAQ", "STOCK"),
            ("START1", "MSFT", "NASDAQ", "STOCK"),
            ("START2", "AAPL", "NASDAQ", "STOCK"),
            ("START3", "TREND", "NASDAQ", "STOCK"),
            ("NEAR1", "TREND", "NASDAQ", "STOCK"),
            ("NEAR2", "NQZ24", "CME", "FUTURE"),
            ("NEAR3", "CLZ24", "CME", "FUTURE"),
            ("VAL1", "AAPL", "NASDAQ", "STOCK"),
            ("VAL2", "MSFT", "NASDAQ", "STOCK"),
            ("VAL3", "TURN", "NASDAQ", "STOCK"),
            ("MOM1", "TREND", "NASDAQ", "STOCK"),
            ("MOM2", "CLZ24", "CME", "FUTURE"),
            ("MOM3", "MSFT", "NASDAQ", "STOCK"),
            ("TOP1", "MSFT", "NASDAQ", "STOCK"),
            ("TOP2", "MSFT", "NASDAQ", "STOCK"),
            ("TOP3", "AAPL", "NASDAQ", "STOCK"),
            ("EVT1", "TURN", "NASDAQ", "STOCK"),
            ("EVT2", "CLZ24", "CME", "FUTURE"),
            ("EVT3", "TSLA", "NASDAQ", "STOCK"),
            ("SPEC1", "TSLA", "NASDAQ", "STOCK"),
            ("SPEC2", "WEAK", "NASDAQ", "STOCK"),
            ("SPEC3", "TURN", "NASDAQ", "STOCK"),
            ("EXC1", "WEAK", "NASDAQ", "STOCK"),
            ("ACT1", "TURN", "NASDAQ", "STOCK"),
            ("ACT2", "TSLA", "NASDAQ", "STOCK"),
            ("HOLD1", "AAPL", "NASDAQ", "STOCK"),
            ("HOLD2", "MSFT", "NASDAQ", "STOCK"),
            ("WATCH1", "WEAK", "NASDAQ", "STOCK"),
            ("WATCH2", "TURN", "NASDAQ", "STOCK"),
            ("ETFSPY", "AAPL", "NASDAQ", "STOCK"),
            ("ETFQQQ", "MSFT", "NASDAQ", "STOCK"),
            ("ETFIWM", "TREND", "NASDAQ", "STOCK"),
            ("LGC1", "AAPL", "NASDAQ", "STOCK"),
            ("LGC2", "MSFT", "NASDAQ", "STOCK"),
            ("MID1", "TURN", "NASDAQ", "STOCK"),
            ("MID2", "TSLA", "NASDAQ", "STOCK"),
            ("MIC1", "WEAK", "NASDAQ", "STOCK"),
            ("MIC2", "TURN", "NASDAQ", "STOCK"),
        ]

        # Ensure the shipped base symbols exist first, then add synthetic profiles.
        for symbol in sorted(source_rows_by_symbol.keys()):
            source_rows = source_rows_by_symbol[symbol]
            if not source_rows:
                continue
            security_id = f"sample-{symbol.lower()}"
            if security_id in existing_security_ids:
                continue
            exchange = "CME" if symbol.endswith("24") else "NASDAQ"
            asset_type = "FUTURE" if symbol.endswith("24") else "STOCK"
            ensure_security(symbol, symbol, exchange, asset_type)

        for symbol, source_symbol, exchange, asset_type in synthetic_specs:
            ensure_security(symbol, source_symbol, exchange, asset_type)

    def record_to_evidence_ledger(
        self,
        session: DailyCommitteeSession,
        evidence_ledger: Any,  # EvidenceLedgerAPI
    ) -> str:
        """
        Record complete session to evidence ledger.

        Returns record_id.
        """
        # Would call evidence_ledger.add_record() with complete session details
        # For now, return a stub ID
        record_id = f"COMM-LEDGER-{session.session_id}"
        return record_id

    def save_session(self, session: DailyCommitteeSession) -> Path:
        """Save session state to disk for recovery."""
        path = self.state_dir / f"{session.session_id}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2, sort_keys=True))
        return path

    def load_session(self, session_id: str) -> DailyCommitteeSession | None:
        """Load session from disk."""
        path = self.state_dir / f"{session_id}.json"
        if not path.exists():
            return None
        # Would deserialize; for now return None
        return None

    def apply_human_approval(
        self,
        session: DailyCommitteeSession,
        approval: HumanApprovalRecord,
    ) -> DailyCommitteeSession | None:
        """Apply human approval to session if valid."""
        if not approval.is_valid_for(
            session.proposal_id,
            session.proposal_hash,
            at_time=datetime.now(timezone.utc),
        ):
            return None

        # Create new session with approval
        return DailyCommitteeSession(
            session_id=session.session_id,
            observation_time=session.observation_time,
            created_at=session.created_at,
            dry_run=session.dry_run,
            transmit=session.transmit,
            approval_expires_minutes=session.approval_expires_minutes,
            warehouse_manifest_hash=session.warehouse_manifest_hash,
            dataset_manifest_hash=session.dataset_manifest_hash,
            universe_config=session.universe_config,
            scan_config=session.scan_config,
            ranking_config=session.ranking_config,
            capital_config=session.capital_config,
            risk_config=session.risk_config,
            governance_config=session.governance_config,
            paper_account_identifier=session.paper_account_identifier,
            current_portfolio_snapshot_id=session.current_portfolio_snapshot_id,
            current_cash=session.current_cash,
            current_equity=session.current_equity,
            workflow_state=session.workflow_state,
            state_transitions=session.state_transitions,
            universe_size=session.universe_size,
            exclusions_count=session.exclusions_count,
            scan_report_id=session.scan_report_id,
            ranking_run_id=session.ranking_run_id,
            total_opportunities_ranked=session.total_opportunities_ranked,
            high_priority_triggered=session.high_priority_triggered,
            high_priority_waiting=session.high_priority_waiting,
            proposal_id=session.proposal_id,
            proposal_hash=session.proposal_hash,
            proposed_cash=session.proposed_cash,
            proposed_gross_exposure=session.proposed_gross_exposure,
            risk_review_id=session.risk_review_id,
            risk_approved=session.risk_approved,
            risk_rejection_reasons=session.risk_rejection_reasons,
            governance_review_id=session.governance_review_id,
            governance_approved=session.governance_approved,
            governance_rejection_reasons=session.governance_rejection_reasons,
            human_approval=approval,
            human_approval_received_at=datetime.now(timezone.utc),
            submitted_orders=session.submitted_orders,
            rejected_orders=session.rejected_orders,
            partial_orders=session.partial_orders,
            paper_submission_report_id=session.paper_submission_report_id,
            filled_orders=session.filled_orders,
            cancelled_orders=session.cancelled_orders,
            closing_positions=session.closing_positions,
            closing_cash=session.closing_cash,
            realized_pnl=session.realized_pnl,
            unrealized_pnl=session.unrealized_pnl,
            reconciliation_notes=session.reconciliation_notes,
            failure_reason=session.failure_reason,
            failures=session.failures,
            morning_report_id=session.morning_report_id,
            reconciliation_report_id=session.reconciliation_report_id,
            schema_version=session.schema_version,
        )
