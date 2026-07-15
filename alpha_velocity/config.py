from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class BrokerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 71
    account: str = ""
    mode: Literal["PAPER", "LIVE"] = "PAPER"
    connect_timeout_seconds: int = 15


class ExecutionConfig(BaseModel):
    dry_run: bool = True
    default_exchange: str = "SMART"
    default_currency: str = "USD"
    order_ref_prefix: str = "ALPHA_VELOCITY"
    outside_rth: bool = False


class RiskConfig(BaseModel):
    starting_equity_fallback: float = 10_000
    max_single_position_pct: float = Field(default=0.20, ge=0, le=1)
    exceptional_position_pct: float = Field(default=0.40, ge=0, le=1)
    absolute_position_cap_pct: float = Field(default=0.80, ge=0, le=1)
    max_gross_exposure_pct: float = Field(default=1.00, ge=0)
    max_daily_loss_pct: float = Field(default=0.03, ge=0, le=1)
    max_strategy_risk_pct: float = Field(default=0.10, ge=0, le=1)
    max_risk_per_trade_pct: float = Field(default=0.01, ge=0, le=1)
    max_order_notional_pct: float = Field(default=0.20, ge=0, le=1)
    max_open_orders: int = 10
    require_stop: bool = True
    minimum_reward_to_risk: float = 2.0
    max_spread_pct: float = 0.015
    max_participation_rate: float = 0.05
    allow_shorting: bool = False
    allow_futures: bool = True
    allow_options: bool = False

    @model_validator(mode="after")
    def validate_tiers(self) -> "RiskConfig":
        if not (
            self.max_single_position_pct
            <= self.exceptional_position_pct
            <= self.absolute_position_cap_pct
        ):
            raise ValueError("Position concentration tiers must be increasing.")
        return self


class LoggingConfig(BaseModel):
    audit_path: str = "./audit/alpha_velocity_audit.jsonl"
    level: str = "INFO"


class AppConfig(BaseModel):
    broker: BrokerConfig
    execution: ExecutionConfig
    risk: RiskConfig
    logging: LoggingConfig


def load_config(path: str | Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
