from __future__ import annotations


class PaperAccountGateError(PermissionError):
    pass


def require_ibkr_paper_account(
    configured_mode: str,
    accounts: list[str],
    dry_run: bool,
) -> None:
    """
    Hard gate for automatic paper execution.

    IBKR paper account identifiers normally begin with DU. Automatic execution
    is refused if the connected account cannot be positively identified as paper.
    """
    if configured_mode != "PAPER":
        raise PaperAccountGateError("Automatic paper trading requires broker.mode=PAPER.")
    if dry_run:
        raise PaperAccountGateError(
            "Paper order transmission requires execution.dry_run=false in config.paper.yaml."
        )
    if not accounts:
        raise PaperAccountGateError("No managed IBKR account identifiers were received.")
    non_paper = [account for account in accounts if not account.upper().startswith("DU")]
    if non_paper:
        raise PaperAccountGateError(
            "Automatic execution blocked because a connected account does not look like "
            f"an IBKR paper account: {non_paper!r}"
        )
