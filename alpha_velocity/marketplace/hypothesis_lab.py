"""Trade Hypothesis Lab - adapter for human-authored hypotheses."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .models import HumanHypothesis


class TradeHypothesisAdapter:
    """Load and validate human-authored hypotheses from YAML/JSON."""

    REQUIRED_FIELDS = [
        "symbol",
        "security_id",
        "author",
        "thesis_text",
        "rationale",
        "required_confirmation",
        "invalidation_trigger",
    ]

    def load_from_yaml(self, yaml_path: str | Path) -> HumanHypothesis:
        """Load hypothesis from YAML file.

        Args:
            yaml_path: Path to YAML hypothesis file

        Returns:
            HumanHypothesis object

        Raises:
            ValueError: If schema is invalid
            FileNotFoundError: If file doesn't exist
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Hypothesis file not found: {yaml_path}")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("YAML must contain a dictionary")

        return self._parse_hypothesis(data, yaml_path=str(yaml_path))

    def load_from_json(self, json_path: str | Path) -> HumanHypothesis:
        """Load hypothesis from JSON file.

        Args:
            json_path: Path to JSON hypothesis file

        Returns:
            HumanHypothesis object

        Raises:
            ValueError: If schema is invalid
            FileNotFoundError: If file doesn't exist
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"Hypothesis file not found: {json_path}")

        with open(json_path) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("JSON must contain a dictionary")

        return self._parse_hypothesis(data, yaml_path=str(json_path))

    def load_from_dict(self, data: dict[str, Any], source_path: str = "") -> HumanHypothesis:
        """Load hypothesis from dictionary.

        Args:
            data: Dictionary with hypothesis data
            source_path: Optional path reference

        Returns:
            HumanHypothesis object

        Raises:
            ValueError: If schema is invalid
        """
        return self._parse_hypothesis(data, yaml_path=source_path)

    def _parse_hypothesis(self, data: dict[str, Any], yaml_path: str = "") -> HumanHypothesis:
        """Parse and validate hypothesis data.

        Args:
            data: Raw hypothesis dictionary
            yaml_path: Source file path

        Returns:
            Validated HumanHypothesis

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Check required fields
        missing = [f for f in self.REQUIRED_FIELDS if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Generate IDs
        hypothesis_id = data.get("hypothesis_id", f"HYP-{uuid.uuid4().hex[:8]}")

        # Parse timestamps
        observation_time_str = data.get("observation_time")
        if observation_time_str:
            observation_time = datetime.fromisoformat(observation_time_str)
        else:
            observation_time = datetime.now(timezone.utc)

        if observation_time.tzinfo is None:
            observation_time = observation_time.replace(tzinfo=timezone.utc)

        created_at_str = data.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str)
        else:
            created_at = datetime.now(timezone.utc)

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        # Parse confidence
        author_confidence = float(data.get("author_confidence", 0.5))
        if not 0.0 <= author_confidence <= 1.0:
            raise ValueError(f"author_confidence must be 0.0-1.0, got {author_confidence}")

        # Parse allocation influence
        allocation_influence_allowed = bool(data.get("allocation_influence_allowed", False))

        return HumanHypothesis(
            hypothesis_id=hypothesis_id,
            symbol=str(data["symbol"]).upper(),
            security_id=str(data["security_id"]),
            author=str(data["author"]),
            created_at=created_at,
            observation_time=observation_time,
            thesis_text=str(data["thesis_text"]),
            rationale=str(data["rationale"]),
            required_confirmation=str(data["required_confirmation"]),
            invalidation_trigger=str(data["invalidation_trigger"]),
            author_confidence=author_confidence,
            allocation_influence_allowed=allocation_influence_allowed,
            source_yaml_path=yaml_path,
        )

    def validate_schema(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate hypothesis schema without creating object.

        Args:
            data: Hypothesis dictionary

        Returns:
            Tuple of (valid, error_messages)
        """
        errors: list[str] = []

        # Check required fields
        missing = [f for f in self.REQUIRED_FIELDS if f not in data]
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")

        # Validate types
        if "symbol" in data and not isinstance(data["symbol"], str):
            errors.append("symbol must be a string")

        if "author_confidence" in data:
            try:
                conf = float(data["author_confidence"])
                if not 0.0 <= conf <= 1.0:
                    errors.append("author_confidence must be 0.0-1.0")
            except (ValueError, TypeError):
                errors.append("author_confidence must be a number")

        # Validate dates
        if "observation_time" in data:
            try:
                datetime.fromisoformat(str(data["observation_time"]))
            except ValueError:
                errors.append("observation_time must be ISO format datetime")

        if "created_at" in data:
            try:
                datetime.fromisoformat(str(data["created_at"]))
            except ValueError:
                errors.append("created_at must be ISO format datetime")

        return len(errors) == 0, errors


def create_hypothesis_template() -> str:
    """Create a blank hypothesis YAML template.

    Returns:
        YAML template as string
    """
    return """# Trade Hypothesis Template
# Fill in all required fields with your research

hypothesis_id: null  # Auto-generated if omitted
symbol: "SYMBOL"
security_id: "SEC_ID"
author: "Your Name"
created_at: null  # Auto-populated if omitted (ISO datetime)
observation_time: "2026-07-16T00:00:00Z"  # ISO datetime

# Core hypothesis fields (required)
thesis_text: |
  One to three sentences describing the core thesis for repricing.
  Why should this equity move materially higher over the next 6 months?

rationale: |
  Detailed explanation of the business, asset value, or capital-stack improvement.
  What is the market missing? Why is now the right time?

required_confirmation: |
  What must happen to confirm the thesis is playing out?
  (e.g., "Price closes above $50 on strong volume")

invalidation_trigger: |
  What breaks the thesis?
  (e.g., "Quarterly guidance cut or covenant breach")

# Optional fields
author_confidence: 0.7  # 0.0-1.0, default 0.5
allocation_influence_allowed: false  # Always false initially (zero influence)
"""
