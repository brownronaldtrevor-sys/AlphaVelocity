from __future__ import annotations

PROHIBITED_BEHAVIORS = (
    "Spoofing, layering, wash trading, marking the close, or deceptive order placement.",
    "Trading on material non-public information or restricted information.",
    "Circumventing exchange, broker, legal, regulatory, account, or risk controls.",
    "Generating false market signals or coordinating manipulative activity.",
    "Using stolen, unlawfully obtained, or privacy-violating data.",
    "Automatically enabling live trading without a separately reviewed release.",
)

REQUIRED_PRACTICES = (
    "Point-in-time data lineage and version history.",
    "Paper-only default and positive paper-account verification.",
    "Forecast journaling before orders.",
    "Human approval before automatic paper transmission.",
    "Risk limits independent from strategy logic.",
    "Immutable audit events for decisions, orders, fills, and overrides.",
    "Reproducible model training and documented validation.",
    "Explicit conflict, restricted-information, and emergency-halt procedures.",
)
