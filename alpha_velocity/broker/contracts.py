from __future__ import annotations

try:
    from ibapi.contract import Contract
except ImportError:  # Allows tests that do not have IBKR installed.
    Contract = object  # type: ignore[misc,assignment]

from alpha_velocity.models import AssetClass, Instrument


def to_ib_contract(instrument: Instrument):
    if Contract is object:
        raise RuntimeError(
            "Official IBKR TWS Python API is not installed. Install it from "
            "the IBKR TWS API distribution before connecting."
        )

    contract = Contract()
    contract.symbol = instrument.symbol
    contract.currency = instrument.currency

    if instrument.asset_class == AssetClass.STOCK:
        contract.secType = "STK"
        contract.exchange = instrument.exchange
        if instrument.primary_exchange:
            contract.primaryExchange = instrument.primary_exchange
    elif instrument.asset_class == AssetClass.FUTURE:
        contract.secType = "FUT"
        contract.exchange = instrument.exchange
        contract.lastTradeDateOrContractMonth = instrument.expiry or ""
        if instrument.multiplier:
            contract.multiplier = instrument.multiplier
    elif instrument.asset_class == AssetClass.OPTION:
        raise NotImplementedError("Option contract construction is intentionally disabled in v0.1.")
    else:
        raise ValueError(f"Unsupported asset class: {instrument.asset_class}")

    return contract
