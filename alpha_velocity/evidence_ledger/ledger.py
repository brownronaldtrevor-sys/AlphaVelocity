"""
Append-only evidence ledger storage and query engine.

Guarantees immutability, tracks revisions, and supports deterministic queries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Mapping, Any
from uuid import uuid4
import json

from alpha_velocity.evidence_ledger.models import (
    EvidenceLedgerRecord,
    SupVersionRecord,
    RecordType,
    ValidationStatus,
)


class AppendOnlyLedger:
    """Immutable append-only ledger for evidence records."""
    
    def __init__(self) -> None:
        """Initialize empty ledger."""
        self._records: list[EvidenceLedgerRecord] = []
        self._record_id_index: dict[str, int] = {}  # record_id -> list position
        self._supersession_index: dict[str, str] = {}  # supersedes_record_id -> record_id
    
    def add_record(self, record: EvidenceLedgerRecord) -> str:
        """
        Add a new record to the ledger.
        
        Args:
            record: The evidence ledger record to add
            
        Returns:
            record_id
            
        Raises:
            ValueError: If record violates append-only invariants
        """
        # Validate immutability: cannot re-record same record_id
        if record.record_id in self._record_id_index:
            existing = self._records[self._record_id_index[record.record_id]]
            if existing != record:
                raise ValueError(
                    f"Record {record.record_id} already exists with different content; "
                    "cannot mutate. Create new revision with supersedes_record_id instead."
                )
            return record.record_id
        
        # Validate supersession if present
        if record.supersession and record.supersession.supersedes_record_id:
            if record.supersession.supersedes_record_id not in self._record_id_index:
                raise ValueError(
                    f"Superseded record {record.supersession.supersedes_record_id} not found"
                )
            
            # Mark the superseded record
            self._supersession_index[record.supersession.supersedes_record_id] = record.record_id
        
        # Store record
        position = len(self._records)
        self._records.append(record)
        self._record_id_index[record.record_id] = position
        
        return record.record_id
    
    def get_record(self, record_id: str) -> EvidenceLedgerRecord | None:
        """Get a record by ID."""
        if record_id not in self._record_id_index:
            return None
        position = self._record_id_index[record_id]
        return self._records[position]
    
    def get_records_by_symbol(
        self,
        symbol: str,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records for a symbol, optionally including superseded records."""
        records = [r for r in self._records if r.symbol == symbol]
        
        if not include_superseded:
            # Filter out superseded records
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_records_by_security_id(
        self,
        security_id: str,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records for a security ID."""
        records = [r for r in self._records if r.security_id == security_id]
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_records_by_date(
        self,
        date: datetime,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records for a specific observation date."""
        records = [
            r for r in self._records
            if r.observation_time.date() == date.date()
        ]
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_records_by_opportunity_id(
        self,
        opportunity_id: str,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records for an opportunity ID."""
        records = [r for r in self._records if r.opportunity_id == opportunity_id]
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_records_by_ranking_run(
        self,
        ranking_run_id: str,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records from a ranking run."""
        records = [r for r in self._records if r.ranking_run_id == ranking_run_id]
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_records_by_capital_proposal(
        self,
        capital_proposal_id: str,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records linked to a capital allocation proposal."""
        records = [r for r in self._records if r.capital_proposal_id == capital_proposal_id]
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_supersession_chain(self, record_id: str) -> Sequence[EvidenceLedgerRecord]:
        """Get the chain of revisions for a record."""
        chain = []
        current_id = record_id
        
        while current_id is not None:
            record = self.get_record(current_id)
            if record is None:
                break
            chain.append(record)
            
            # Find next revision
            current_id = self._supersession_index.get(current_id)
        
        return chain
    
    def get_ungraded_records(self) -> Sequence[EvidenceLedgerRecord]:
        """Get records that have not yet received outcome grades."""
        records = [
            r for r in self._records
            if len(r.outcome_grades) == 0
        ]
        
        # Exclude superseded
        superseded_ids = set(self._supersession_index.keys())
        records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_shadow_research_records(self) -> Sequence[EvidenceLedgerRecord]:
        """Get records that used shadow (unvalidated) research evidence."""
        records = []
        for r in self._records:
            if (r.influence_weights.expectations_ranking_influence == 0.0 or
                r.influence_weights.expectations_validation_status == "SHADOW" or
                r.influence_weights.sentiment_validation_status == "SHADOW"):
                records.append(r)
        
        # Exclude superseded
        superseded_ids = set(self._supersession_index.keys())
        records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)
    
    def get_all_records(
        self,
        include_superseded: bool = False,
        sorted_by_time: bool = True,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Get all records in ledger."""
        records = list(self._records)
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        if sorted_by_time:
            records = sorted(records, key=lambda r: r.observation_time)
        
        return records
    
    def get_record_count(self, include_superseded: bool = False) -> int:
        """Get total record count."""
        if include_superseded:
            return len(self._records)
        superseded_ids = set(self._supersession_index.keys())
        return sum(1 for r in self._records if r.record_id not in superseded_ids)
    
    def to_json(self) -> str:
        """Serialize entire ledger to JSON."""
        records_data = [r.to_dict() for r in self._records]
        return json.dumps(records_data, default=str, sort_keys=True, indent=2)
    
    def export_records_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        include_superseded: bool = False,
    ) -> Sequence[EvidenceLedgerRecord]:
        """Export records within date range."""
        records = [
            r for r in self._records
            if start_date.date() <= r.observation_time.date() <= end_date.date()
        ]
        
        if not include_superseded:
            superseded_ids = set(self._supersession_index.keys())
            records = [r for r in records if r.record_id not in superseded_ids]
        
        return sorted(records, key=lambda r: r.observation_time)


def generate_record_id() -> str:
    """Generate a unique record ID."""
    return f"LEG-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:12]}"


def create_revision_record(
    original_record: EvidenceLedgerRecord,
    revision_reason: str,
    changes: Mapping[str, Any],
) -> EvidenceLedgerRecord:
    """
    Create a revised record that supersedes an original.
    
    Args:
        original_record: The record being revised
        revision_reason: Why the record is being revised
        changes: Dictionary of changed fields (will override original values)
        
    Returns:
        New EvidenceLedgerRecord with supersession link
    """
    from dataclasses import replace
    
    # Use dataclass replace to create new record with changes
    # This properly handles nested structures
    updated_record = replace(
        original_record,
        record_id=generate_record_id(),
        created_at=datetime.now(timezone.utc),
        **changes
    )
    
    # Create supersession record
    supersession = SupVersionRecord(
        record_id=updated_record.record_id,
        supersedes_record_id=original_record.record_id,
        record_type=RecordType.REVISION.value,
        revision_reason=revision_reason,
        revised_at=datetime.now(timezone.utc),
    )
    
    # Create final record with supersession
    return replace(
        updated_record,
        supersession=supersession,
    )
