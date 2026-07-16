# Alpha Velocity Architecture

## 1. North-star objective

Alpha Velocity exists to maximize expected long-term compound growth by identifying, validating, ranking, allocating capital to, executing, and continuously learning from the highest expected-value opportunities, subject to risk, liquidity, execution, and governance constraints.

This platform is an evidence-driven decision system, not a promise of profit. It is designed to support disciplined research, controlled experimentation, and auditable execution under explicit institutional safeguards.

## 2. Investment orientation

Alpha Velocity is oriented toward research and execution of probabilistic opportunities rather than deterministic predictions.

The platform supports:
- swing-trade horizons
- breakout and inflection-point research
- weekly context with daily triggers
- support and resistance levels
- volatility contraction and expansion
- relative strength
- catalysts
- opportunity-cost comparisons
- dynamic allocation toward the strongest validated opportunities

These are hypotheses and evidence streams, not guaranteed alpha. No signal receives portfolio weight until it demonstrates incremental out-of-sample value after costs.

## 3. Major bounded modules

The system is divided into bounded responsibilities so that evidence, risk, execution, and learning remain separable and auditable.

### Warehouse
Responsibilities:
- Persist provider-neutral historical market and reference data.
- Preserve point-in-time integrity using occurred_at and available_at semantics.
- Retain security identity, ticker history, corporate actions, delistings, and market data.
- Store failure records and ingestion manifests for reproducibility.

Inputs:
- External provider snapshots and periodic refreshes.

Outputs:
- Canonical security and bar history.
- Point-in-time universe views.
- Deterministic manifests and quality summaries.

Prohibited responsibilities:
- Ranking opportunities.
- Approving allocations.
- Mutating portfolio, risk, or broker state.

### Feature Store and Validation
Responsibilities:
- Build point-in-time features and labels from warehouse data.
- Enforce leakage controls, observation windows, and out-of-sample splitting.
- Produce validation datasets and manifests.

Inputs:
- Warehouse bars, securities, corporate actions, and metadata.

Outputs:
- Feature rows, labels, validation datasets, and manifests.

Prohibited responsibilities:
- Deciding portfolio weights.
- Bypassing governance or risk controls.
- Creating live orders or fills.

### Opportunity Intelligence
Responsibilities:
- Generate hypotheses from research evidence, market structure, and signal logic.
- Score and rank opportunities using evidence streams that are consistent with validation outcomes.
- Provide candidate proposals for portfolio evaluation.

Inputs:
- Feature-store outputs, research signals, and market context.

Outputs:
- Ranked candidate opportunities and decision rationale.

Prohibited responsibilities:
- Directly approving allocations.
- Mutating risk or execution state.
- Escaping validation and audit requirements.

### Research Lab
Responsibilities:
- Support experiment design, hypothesis testing, and historical evaluation.
- Compare strategies and feature sets under realistic constraints.
- Measure out-of-sample performance and calibration.

Inputs:
- Warehouse data, feature sets, model variants, and reporting requirements.

Outputs:
- Validation reports, experiment results, and promotion recommendations.

Prohibited responsibilities:
- Bypassing governance approvals.
- Issuing live orders.
- Defining final risk limits without independent review.

### Event-Driven Backtester
Responsibilities:
- Reproduce strategy behavior over time under realistic market events and constraints.
- Model execution slippage, liquidity, and partial fills as part of the simulation.
- Produce realistic performance evidence for promotion decisions.

Inputs:
- Historical data, candidate strategies, and execution assumptions.

Outputs:
- Backtest metrics, event logs, and scenario analyses.

Prohibited responsibilities:
- Approving live deployment.
- Mutating portfolio state outside the simulation envelope.

### Portfolio Intelligence
Responsibilities:
- Evaluate candidate opportunities against existing holdings and current portfolio constraints.
- Optimize marginal expected contribution rather than isolated standalone value.
- Manage concentration, correlation, turnover, and rebalancing trade-offs.

Inputs:
- Validated candidate proposals and portfolio state.

Outputs:
- Allocation recommendations and rebalance plans.

Prohibited responsibilities:
- Approving or rejecting its own models without independent review.
- Bypassing risk controls.
- Sending broker instructions directly.

### Execution
Responsibilities:
- Translate approved portfolio decisions into actionable order logic.
- Preserve expected value through limit and stop logic, participation rules, spread and slippage handling, market impact awareness, and protective exits.
- Maintain auditability for every instruction issued.

Inputs:
- Approved allocation decisions and execution policy.

Outputs:
- Orders, partial-fill plans, and execution audit records.

Prohibited responsibilities:
- Inventing forecast signals.
- Replacing governance or independent risk approval.
- Mutating portfolio state outside approved execution workflows.

### Continuous Learning
Responsibilities:
- Update models, heuristics, and workflows from observed outcomes and audit records.
- Compare predicted and realized results.
- Feed evidence back into research and validation.

Inputs:
- Outcomes, fills, audit logs, and validation results.

Outputs:
- Learning reports, calibration updates, and promotion or quarantine recommendations.

Prohibited responsibilities:
- Silently overriding governance decisions.
- Automating live transitions without explicit approval.

### Investment Genome
Responsibilities:
- Capture reusable strategy, feature, and process knowledge across experiments and production-like workflows.
- Track lineage, assumptions, and evidence for each approach.

Inputs:
- Research outputs, validated features, promotion outcomes, and operational learnings.

Outputs:
- Strategy and feature lineage, reusable knowledge objects, and promotion history.

Prohibited responsibilities:
- Replacing independent research validation.
- Bypassing point-in-time discipline.

### Knowledge Graph
Responsibilities:
- Connect hypotheses, market events, features, strategies, outcomes, and governance artifacts into a searchable evidence network.
- Support cross-domain reasoning and audit exploration.

Inputs:
- Structured records from warehouse, research, portfolio, execution, and learning modules.

Outputs:
- Traceable evidence relationships and navigation across system artifacts.

Prohibited responsibilities:
- Making allocation decisions on its own.
- Holding or enforcing risk policies without oversight.

### Governance and Risk
Responsibilities:
- Set independent policy boundaries and approval gates.
- Validate that research and execution operations remain within defined risk and ethics constraints.
- Enforce paper-first defaults and controlled live-transition rules.

Inputs:
- Proposals, portfolio decisions, execution requests, and operational events.

Outputs:
- Approvals, rejections, quarantines, and incident records.

Prohibited responsibilities:
- Becoming a second implementation of strategy logic.
- Approving its own research or allocation recommendations without independent review.

### Broker and External Interfaces
Responsibilities:
- Connect to brokers, data providers, and external services through explicit adapters.
- Translate provider and broker events into canonical internal representations.

Inputs:
- Market data feeds, broker messages, account state, and provider metadata.

Outputs:
- Normalized data and event streams.

Prohibited responsibilities:
- Bypassing governance, risk, or audit controls.
- Executing live orders without an approved workflow.

### Reporting and Evidence Ledger
Responsibilities:
- Preserve immutable records of hypotheses, actions, outcomes, and decisions.
- Provide evidence for review, debugging, compliance, and continuous learning.

Inputs:
- Audit events, manifests, portfolios, fills, validation results, and governance decisions.

Outputs:
- Evidence ledger entries, reports, and review summaries.

Prohibited responsibilities:
- Altering historical records to conceal failures.
- Replacing independent validation with presentation-only summaries.

## 4. Dependency direction

The architecture should follow a single, explicit dependency flow:

External providers
→ Warehouse
→ Feature Store
→ Research and Opportunity Intelligence
→ Portfolio Intelligence
→ Independent Governance and Risk approval
→ Execution interface
→ Broker

Outcomes and audit records
→ Evidence Ledger
→ Continuous Learning
→ Research validation

Rules:
- Dependencies must flow in one direction and avoid circular references.
- Strategies must not mutate portfolio, fills, risk decisions, or broker state directly.
- Governance and risk remain independent of the research and execution path.
- The warehouse is a shared foundation, not a domain-specific decision engine.

## 5. Point-in-time rules

Alpha Velocity must preserve point-in-time discipline in all data use and decision recording.

The required rules are:
- available_at governs visibility.
- occurred_at and available_at are distinct concepts.
- No future rows may be visible to a decision at its observation time.
- Completed daily bars cannot fill at the same close as the observation.
- Incomplete weekly bars cannot be exposed as completed weekly bars.
- Current surviving tickers cannot define historical universes.
- Raw prices remain separate from adjusted research prices.
- Delisted securities and provider failures are retained rather than silently discarded.

## 6. Research promotion lifecycle

Every research idea should advance through a staged lifecycle:

Hypothesis
→ implementation
→ historical validation
→ purged walk-forward validation
→ realistic backtest
→ supervised paper trading
→ calibration review
→ promotion, limited weight, quarantine, or rejection

Promotion is a cautious evidence-based decision. It should never be treated as a guarantee of profitability.

## 7. Expected-value framework

The platform evaluates opportunities by expected value rather than simple win-rate optimization.

Ranking should ultimately consider:
- calibrated probability
- expected upside
- expected downside
- time horizon
- liquidity
- transaction costs
- uncertainty
- correlation
- capacity
- opportunity cost

These factors are not hard-coded in this document. Their weighting should emerge from validation evidence and should be reviewed as part of the calibration process.

## 8. Portfolio principles

Portfolio construction should preserve and improve long-term expected value rather than chasing isolated signal quality.

Core principles:
- Compare candidates against existing holdings.
- Allocate based on marginal expected contribution.
- Account for turnover and switching costs.
- Cap concentration and correlated exposure.
- Reduce or exit when the thesis or relative opportunity deteriorates.
- Prediction models cannot approve their own allocations.

## 9. Execution principles

Execution preserves expected value rather than creating unsupported forecasts.

Execution should account for:
- limit and stop logic
- partial fills
- liquidity participation
- spread
- slippage
- market impact
- protective exits
- auditability

Execution logic must remain consistent with the portfolio thesis and risk controls, not attempt to manufacture new alpha.

## 10. Governance principles

Governance and risk remain independent.

Required principles:
- No live execution path should be enabled merely because research succeeded historically.
- Paper and research modes remain default until explicitly approved through a separate controlled process.
- Research evidence must be retained, reviewable, and reproducible.
- Ethical and regulatory boundaries remain binding even when strategy performance is strong.

## 11. Repository placement guide

This milestone does not require a disruptive refactor. The repository should continue to use its existing package structure while gradually aligning modules to the architecture above.

Recommended placement:
- Existing: alpha_velocity/warehouse/ for warehouse and canonical historical storage.
- Existing: alpha_velocity/validation/ for leakage-controlled feature building and validation datasets.
- Existing: alpha_velocity/research/ for research-oriented workflows and evidence generation.
- Existing: alpha_velocity/portfolio/ for portfolio allocation and position-level decision logic.
- Existing: alpha_velocity/risk/ for independent risk evaluation and policy enforcement.
- Existing: alpha_velocity/governance/ for governance controls and approval boundaries.
- Existing: alpha_velocity/broker/ for provider and broker interfaces.
- Existing: alpha_velocity/learning/ for continuous learning and evidence assimilation.
- Future: alpha_velocity/investment_genome/ or alpha_velocity/genome/ for reusable strategy knowledge.
- Future: alpha_velocity/knowledge_graph/ for evidence-relationship modeling.
- Future: alpha_velocity/execution/ for execution-specific orchestration if the codebase later grows beyond the current broker boundary.

The current organization is already close to this model. The priority is clarity and bounded responsibilities, not a large reorganization.

## 12. Pull-request standards

Every major pull request should document:
- hypothesis or operational purpose
- success criteria
- rejection criteria
- tests
- point-in-time implications
- risk implications
- expected-value contribution
- unresolved limitations

A PR should not be considered complete if the evidence trail is ambiguous or if the change weakens the independent controls.

## 13. Architecture decision records

A future docs/adr directory should be used for significant architectural decisions.

An ADR is recommended when a change:
- introduces a new subsystem or dependency direction
- changes governance, risk, or execution boundaries
- changes point-in-time or data lineage rules
- materially affects research promotion or portfolio allocation behavior

## 14. Non-goals

Alpha Velocity does not:
- guarantee returns
- treat chart patterns as certainty
- use backtests as proof of future profitability
- allow models to bypass risk controls
- silently discard failed data
- optimize isolated win rate at the expense of compound growth

The mission is disciplined evidence generation, controlled execution, and continuous learning under explicit constraints.
