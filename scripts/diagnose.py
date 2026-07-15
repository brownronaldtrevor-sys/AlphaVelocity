from __future__ import annotations

import importlib.util
import json
import platform
import socket
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"


def test_port(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "TCP connection succeeded"
    except OSError as exc:
        return False, str(exc)


def main() -> int:
    result: dict[str, object] = {
        "python": sys.version,
        "platform": platform.platform(),
        "project_root": str(ROOT),
        "alpha_velocity_importable": importlib.util.find_spec("alpha_velocity") is not None,
        "ibapi_importable": importlib.util.find_spec("ibapi") is not None,
        "config_exists": CONFIG.exists(),
    }

    if CONFIG.exists():
        raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        broker = raw.get("broker", {})
        execution = raw.get("execution", {})
        host = str(broker.get("host", "127.0.0.1"))
        port = int(broker.get("port", 7497))
        ok, detail = test_port(host, port)
        result.update(
            {
                "broker_host": host,
                "broker_port": port,
                "broker_mode": broker.get("mode"),
                "dry_run": execution.get("dry_run"),
                "socket_open": ok,
                "socket_detail": detail,
            }
        )

    print(json.dumps(result, indent=2))

    failures = []
    if not result["alpha_velocity_importable"]:
        failures.append("Alpha Velocity package is not installed in this environment.")
    if not result["ibapi_importable"]:
        failures.append("Official IBKR Python API (ibapi) is not installed in this environment.")
    if not result["config_exists"]:
        failures.append("config.yaml is missing.")
    if result.get("socket_open") is False:
        failures.append("TWS/IB Gateway socket is not reachable at the configured host/port.")

    if failures:
        print("\nNOT READY:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nREADY FOR READ-ONLY CONNECTION TEST.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
