# Security Policy

## Secrets

Never commit:

- IBKR passwords or two-factor authentication codes
- account recovery information
- withdrawal or banking information
- API secrets
- account-specific `config.yaml`
- `.env` files
- audit logs or research journals containing sensitive information

These files are excluded by `.gitignore`.

## Reporting

Treat any bypass of the paper-account gate, risk limits, kill switch, audit logging,
or restricted-information controls as a critical defect. Do not use the affected build
for order transmission until the defect is fixed and tested.
