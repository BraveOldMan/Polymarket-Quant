# Polymarket Quant

> Read-only Polymarket prediction-market arbitrage research framework with schema-validated data,
> offline replay, and fail-closed safety boundaries.

Polymarket Quant is a Python research system for prediction-market arbitrage. The current
implementation focuses on a P1 offline, read-only loop: validated market data, deterministic replay,
structural and latency-arbitrage signal detection, wash/liquidity filters, and safety tests that
forbid order creation, signing, approvals, and on-chain writes.

This project is not a live trading bot. It does not place orders, sign messages, broadcast
transactions, split/merge conditional tokens, redeem positions, or manage a wallet.

## Repository Description Metadata

Suggested GitHub repository description:

```text
Read-only Polymarket prediction-market arbitrage research framework with schema-validated data, offline replay, and fail-closed safety boundaries.
```

## Current Status

| Area | Status |
| --- | --- |
| Runtime stage | P1 offline research loop |
| Trading mode | Read-only |
| Live collectors | Interface skeletons only; disabled by default |
| Execution | Not implemented |
| Wallet access | Not implemented |
| Settlement writes | Disabled by `ReadOnlySettlementClient` |
| Replay | Implemented for one binary market fixture |
| Tests | Unit tests cover schemas, filters, replay, and read-only safety |
| Python target | `>=3.14,<3.15` |

Current P1 scope:

- Strategy 1: single-condition structural arbitrage, e.g. `YES + NO < 1 - cost`.
- Strategy 4: latency arbitrage using a Binance price tick as a fair-value anchor.
- Wash-trading heuristic filter based on abnormal order-book structure.
- Exit-liquidity pre-check before accepting a signal.
- Offline replay using `recv_ts` alignment to prevent look-ahead leakage.
- Fail-closed orchestration and settlement stubs.

Out of scope for the current stage:

- Live trading.
- Polymarket CLOB order submission.
- Wallet signing.
- On-chain approvals.
- CTF split/merge.
- NegRisk conversion.
- UMA redemption.
- Automated copy trading.
- Identity hiding, monitoring evasion, or airdrop farming logic.

## Architecture

The long-term design is a six-layer prediction-market arbitrage system:

```text
data and market signals
    -> reasoning and fair-value estimation
    -> orchestration and risk veto
    -> infrastructure
    -> settlement and lifecycle accounting
    -> monitoring and evaluation
```

The implemented P1 slice is intentionally narrower:

```text
offline fixture
    -> pydantic schema validation
    -> wash and liquidity filters
    -> structural and latency signals
    -> read-only risk/orchestration decision
    -> disabled settlement client
```

## Package Layout

```text
.
|-- src/polymarket_quant/
|   |-- data/
|   |   |-- schemas.py                 # Strict pydantic contracts for external data
|   |   |-- collectors/                # Replay and disabled live collector interfaces
|   |   `-- signals/                   # Fair value, structural, latency, filters
|   |-- backtest/
|   |   `-- replay.py                  # Offline replay without look-ahead
|   |-- reasoning/
|   |   `-- contracts.py               # Reasoning-layer contracts
|   |-- risk/
|   |   `-- controls.py                # Risk agent with default kill switch
|   |-- orchestration/
|   |   `-- read_only.py               # Read-only orchestrator, no execution actions
|   |-- settlement/
|   |   `-- read_only.py               # Disabled settlement client
|   `-- infrastructure/
|       `-- settings.py                # Runtime settings
|-- tests/
|   |-- fixtures/offline_replay.json   # Deterministic replay fixture
|   |-- test_replay.py                 # Replay and no-future-data checks
|   |-- test_read_only_safety.py       # No execution/signing/on-chain write patterns
|   |-- test_schemas.py                # Data contract validation
|   |-- test_signals.py                # Signal generation behavior
|   `-- test_filters.py                # Wash/liquidity filters
|-- docs/                              # Design and technical specifications
|-- pyproject.toml                     # Package metadata and dependencies
|-- .env.example                       # Environment template
|-- .github/workflows/                 # CI test workflow
`-- README.md
```

## Safety Model

The repository is intentionally built around read-only boundaries.

Safety guarantees in the current codebase:

- `ReadOnlyOrchestrator` never produces an executable action.
- `RiskAgent` defaults to a kill switch and vetoes signals.
- `ReadOnlySettlementClient` returns `disabled` and never touches a wallet or chain.
- Live Polymarket and Binance collectors are disabled by default and raise explicit errors.
- `tests/test_read_only_safety.py` scans source code for forbidden execution patterns such as:
  - `create_order(...)`
  - `sign_message(...)`
  - `sign_transaction(...)`
  - `approve(...)`
  - `split(...)`
  - `merge(...)`
  - `redeem(...)`
  - `convert(...)`

Any future execution layer must be added as a separate audited stage with explicit risk limits,
event sourcing, idempotency keys, nonce controls, wallet isolation, and paper-trading evidence.

## Data Contracts

All external data must be validated before it enters the signal layer. The main contracts are in
`src/polymarket_quant/data/schemas.py`.

Important models:

| Model | Purpose |
| --- | --- |
| `Market` | Polymarket market metadata |
| `OrderBookSnapshot` | Token order-book snapshot with `event_ts` and local `recv_ts` |
| `PriceTick` | Binance spot/perp tick used as fair-value anchor |
| `FairValueEstimate` | Signal-layer fair probability estimate |
| `ArbSignal` | Read-only arbitrage signal, not an order instruction |
| `MarketGroup` | Future multi-condition mutual-exclusion group |
| `SemanticLink` | Future cross-market semantic equivalence mapping |
| `SettlementIntent` | Future settlement intent shape, currently disabled |

Free-text fields such as market questions and rules are treated as untrusted input. Schema
validation checks format, not semantic truth and not prompt-injection safety.

## Implemented Signals

### Structural Arbitrage

Implemented in:

```text
src/polymarket_quant/data/signals/structural.py
```

The P1 structural signal detects complete-set underpricing:

```text
YES best ask + NO best ask < 1 - estimated cost
```

It only emits a read-only `ArbSignal`. It does not create CLOB orders or invoke CTF split/merge.

### Latency Arbitrage

Implemented in:

```text
src/polymarket_quant/data/signals/latency_arb.py
```

The P1 latency signal compares Polymarket implied probability against a fair-value estimate derived
from a Binance tick. It requires:

- Polymarket and Binance `recv_ts` delta within `delta_max_ms`.
- Edge after cost above the configured threshold.
- Confidence interval that clears the market price.
- Wash filter and exit-liquidity checks passing unless explicitly configured otherwise.

### Wash Filter

Implemented in:

```text
src/polymarket_quant/data/signals/wash_filter.py
```

The current heuristic is conservative. It flags suspicious extreme crossed-book patterns when both
extreme bid and extreme ask sizes are large.

### Exit-Liquidity Filter

Implemented in:

```text
src/polymarket_quant/data/signals/liquidity.py
```

The filter checks whether enough bid-side depth exists within acceptable slippage for a target exit
size.

## Offline Replay

Offline replay is implemented in:

```text
src/polymarket_quant/backtest/replay.py
```

Replay rules:

- Sort events by local receive timestamp `recv_ts`.
- For each YES order-book snapshot, use only NO books and Binance ticks with `recv_ts <= current`.
- Do not use future ticks to fill current signals.
- Count skipped events when required contemporaneous inputs are unavailable.
- Return signals and skipped-event count only.
- Do not compute PnL, Sharpe, or production viability claims in P1.

Fixture:

```text
tests/fixtures/offline_replay.json
```

## Installation

This project currently targets Python 3.14:

```text
requires-python = ">=3.14,<3.15"
```

Create a virtual environment:

```powershell
git clone https://github.com/BraveOldMan/Polymarket-Quant.git
Set-Location .\Polymarket-Quant

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install the package for local development:

```powershell
python -m pip install -e ".[dev]"
```

If some heavy external dependencies are not available for Python 3.14 in your environment, preserve
the installation error evidence and avoid silently changing the Python version. The CI workflow
currently installs only the dependencies touched by tests, because live collectors are not active in
P1.

## Configuration

Use `.env.example` as the template for local environment variables.

Current defaults are read-only. Secrets are not required for offline replay tests.

Do not commit:

- API keys.
- Wallet private keys.
- Mnemonics.
- RPC credentials.
- Polymarket authentication secrets.
- Generated trading logs.

## Usage

### Run Tests

```powershell
python -m pytest
```

Run with coverage:

```powershell
python -m pytest --cov=polymarket_quant --cov-report=term-missing
```

### Run a Low-Side-Effect Syntax Check

```powershell
python -m compileall src tests
```

### Inspect the Offline Replay Fixture in Python

The current replay entrypoint is a library function:

```python
from decimal import Decimal
from datetime import datetime, timezone

from polymarket_quant.backtest.replay import ReplayConfig, run_single_market_replay
```

See `tests/test_replay.py` for a complete deterministic example.

## CI

The GitHub Actions workflow is in:

```text
.github/workflows/
```

The workflow:

- Uses Python 3.14.
- Installs `pydantic` and test dependencies.
- Installs this package with `pip install -e . --no-deps`.
- Runs pytest with coverage.

This intentionally avoids installing live collector dependencies until the project actually imports
and exercises them in tests.

## Development Rules

Key engineering rules for this repository:

- Keep P1 read-only unless a separate execution milestone is explicitly approved.
- Validate external data through Pydantic contracts before signal logic.
- Treat free text as untrusted, especially before any LLM reasoning step.
- Use `recv_ts` for cross-source replay alignment.
- Do not use future data in replay.
- Keep strategy modules parameterized and replaceable.
- Preserve input references in generated signals for auditability.
- Fail closed when data is missing, ambiguous, stale, or unsafe.
- Do not add hidden live-trading paths.
- Do not implement monitoring evasion, identity hiding, or airdrop farming mechanisms.

## Roadmap

Short-term:

- Add CLI wrappers for offline replay.
- Add more offline replay fixtures.
- Expand signal tests across edge cases.
- Add deterministic report output for replay diagnostics.
- Make collector dependencies optional extras.

Medium-term:

- Implement read-only live collectors for Polymarket and Binance.
- Add normalized cache/storage for market snapshots and ticks.
- Add paper-trading simulation with event-sourced state.
- Add portfolio-level risk budgets.
- Add monitoring dashboards.

Long-term, only after research and paper validation:

- Add audited execution intents.
- Add wallet isolation and signing service design.
- Add idempotent settlement lifecycle handling.
- Add human approval gates for high-risk strategy families.

## Known Limitations

- Current implementation is not a profit-generating system.
- Offline replay does not prove live latency edge.
- Live collectors are disabled skeletons.
- No real Polymarket CLOB integration is active.
- No wallet or settlement write path exists.
- No production monitoring exists yet.
- Some declared dependencies may not have complete Python 3.14 wheel support in every environment.
- Design documents under `docs/` are more complete than the current P1 implementation.

## Disclaimer

Prediction markets, crypto assets, and on-chain settlement carry substantial financial, technical,
legal, and operational risk. This repository is for research and engineering study only. Nothing in
this project is financial advice, trading advice, or a recommendation to use Polymarket or any other
market.

## License

No open-source license has been declared yet. Public visibility on GitHub does not automatically
grant permission to copy, modify, redistribute, or use this project commercially.

Contact the repository owner before reusing this code outside personal research.
