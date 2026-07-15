import pytest

from alpha_velocity.paper_auto.account_gate import (
    PaperAccountGateError,
    require_ibkr_paper_account,
)


def test_du_paper_account_passes():
    require_ibkr_paper_account("PAPER", ["DU1234567"], dry_run=False)


def test_live_account_is_blocked():
    with pytest.raises(PaperAccountGateError):
        require_ibkr_paper_account("PAPER", ["U1234567"], dry_run=False)


def test_dry_run_cannot_transmit():
    with pytest.raises(PaperAccountGateError):
        require_ibkr_paper_account("PAPER", ["DU1234567"], dry_run=True)


def test_live_mode_is_blocked():
    with pytest.raises(PaperAccountGateError):
        require_ibkr_paper_account("LIVE", ["DU1234567"], dry_run=False)
