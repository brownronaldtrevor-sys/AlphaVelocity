# Updating Alpha Velocity Without Reinstalling

Do not delete the installed `AlphaVelocity` folder and do not recreate `.venv`.

Future update packages should contain code only.

To apply an update:

1. Save the update ZIP somewhere easy to find.
2. Open PowerShell inside the installed `AlphaVelocity` folder.
3. Run:

```powershell
.\APPLY_UPDATE.ps1 -UpdateZip "C:\path\to\update.zip"
```

The updater:

- preserves `.venv`;
- preserves `config.yaml`;
- preserves reports, state, and logs;
- backs up the current code;
- installs the updated package into the same environment;
- runs the complete test suite;
- refuses the update if tests fail.

The official IBKR API therefore needs to be installed only once.
