from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


class KillSwitch:
    def __init__(self, path: str | Path = "state/kill_switch.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def is_active(self) -> bool:
        if not self.path.exists():
            return False
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return bool(payload.get("active", False))

    def set(self, active: bool, reason: str) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "active": active,
                    "reason": reason,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
