# Release Notes — Clean Ready Build

## Packaging corrections

- One visible project folder only.
- No nested `alpha_velocity_ibkr_v0_1` folder.
- No `.venv`, `__pycache__`, `.pyc`, or local account state included.
- Safe `config.yaml` supplied with `PAPER` and `dry_run: true`.
- Windows one-click setup, diagnostics, tests, and read-only connection launchers.

## Connection corrections

- Supports older and IBKR API 10.33+ error callback signatures.
- Connection command never transmits the synthetic demo strategy.
- Waits for account-summary, position, and open-order completion callbacks.
- Provides local TCP/socket readiness diagnostics before connection.

## Verification

- Clean environment installation completed.
- 26 tests passed.
- Python compilation completed.
