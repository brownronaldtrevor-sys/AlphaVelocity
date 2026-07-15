# Alpha Velocity — Windows First Run

This release has **one project folder**. Do not open an inner folder. The correct folder is the one containing:

- `SETUP_WINDOWS.bat`
- `CONNECT_TWS_READ_ONLY.bat`
- `pyproject.toml`
- `config.yaml`
- `alpha_velocity`
- `tests`

## 1. Extract safely

Extract the ZIP to a simple local location such as:

```text
C:\AlphaVelocity
```

Avoid `C:\Windows`, `Program Files`, and OneDrive for the first setup.

## 2. Install Python

Install Python 3.11 or newer. During installation, select **Add Python to PATH**.

## 3. Install the official IBKR TWS API

Install the official Interactive Brokers TWS API. The normal Windows location is:

```text
C:\TWS API\source\pythonclient
```

The installer script will attempt to find and install that Python client automatically.

## 4. Run the installer

Double-click:

```text
SETUP_WINDOWS.bat
```

It will:

1. create `.venv`;
2. install Alpha Velocity;
3. install development/test dependencies;
4. create a safe paper `config.yaml` if needed;
5. attempt to install the official `ibapi` package;
6. run the full test suite; and
7. run readiness diagnostics.

## 5. Configure TWS Paper

Open Trader Workstation and log into the **paper** account.

Go to:

```text
File → Global Configuration → API → Settings
```

Confirm:

- Enable ActiveX and Socket Clients: **ON**
- Read-Only API: **ON**
- Socket port: **7497** (or change `config.yaml` to match)
- TWS remains open and fully logged in

## 6. Diagnose

Double-click:

```text
DIAGNOSE_TWS.bat
```

The final result should show:

- `alpha_velocity_importable: true`
- `ibapi_importable: true`
- `config_exists: true`
- `socket_open: true`
- `broker_mode: PAPER`
- `dry_run: true`

## 7. Connect safely

Double-click:

```text
CONNECT_TWS_READ_ONLY.bat
```

This command reads account state only. It never submits the synthetic demonstration strategy.

## Important status

This is a research and paper-trading foundation. The predictive heuristics are not validated alpha and are blocked from live readiness. Keep TWS Read-Only enabled during connection testing.
