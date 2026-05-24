# Evidence for autonomy-8nex — Kalshi daily data coverage refresh and capital-readiness verdict

## Artifact produced
- Repo: `/home/exedev/autonomy/labs/trading-research`
- Primary verdict report: `reports/kalshi_readiness_2026-05-24.md`
- Machine-readable verdict: `reports/kalshi_readiness_2026-05-24.json`
- Coverage report: `reports/coverage_report_2026-05-24.md`
- Runner log: `results/daily_run.log`

## Objective run evidence
- `PYTHONUNBUFFERED=1 python3 -u kalshi_daily_runner.py --force` → completed successfully; fetched 46,511 financial markets for run slot `2026-05-24T00:00:00+00:00`, `error=None`, `changed_prices=653`, `new_records=0` because the forced run reused the already-populated slot.
- `python3 kalshi_daily_runner.py --coverage-only` → wrote `reports/coverage_report_2026-05-24.md`; total unique tickers 95,064; 21 distinct run timestamps; 4 distinct days; 40,387 tickers with 8+ snapshots.
- `python3 kalshi_backtest.py` → completed 12 strategy backtests through `2026-05-24`.
- `python3 scripts/kalshi_readiness_diagnostic.py` → wrote JSON+Markdown readiness reports and returned `NOT READY`.
- `python3 tests/test_signals.py` → all 8 synthetic signal tests passed.
- `python3 -m pytest -q` → environment caveat: global Python lacks pytest (`No module named pytest`); repo's direct test runner was used successfully.

## Data coverage summary
- Latest run rows/tickers: 46,511 / 46,511.
- Latest valid-bid rows: 653.
- Latest tradeable/liquid rows (`bid>0`, `volume>0`, `open_interest>0`): 212, below the >=500 broad-coverage gate.
- Valid-price tickers with 2+ calendar days: 599.
- Valid-price tickers with 3+ calendar days: 0.
- Cross-day overlap: 599 valid-price tickers between 2026-05-23 and 2026-05-24.

## Backtest result and capital-readiness verdict
- Verdict: **NOT READY** for capital deployment.
- Reason 1: liquidity/coverage is still thin for a broad strategy gate: only 212 latest tradeable rows.
- Reason 2: 11/12 current strategies lose money; the only positive-PnL strategy (`Volume Breakout`) does **not** clear risk-adjusted gates.
- Best current run: `Volume Breakout`, 33 trades, win rate 12.1%, PnL +$45.00, Sharpe 0.0675, max drawdown 5.17%.
- Gate failure: Sharpe is far below the >0.5 threshold required before paper/live escalation; positive raw PnL alone is not enough.

## Recommendation and next experiment
- Do not paper-trade or deploy capital from this evidence.
- Continue daily snapshots until the 7-day gate, then rerun the same readiness diagnostic.
- Reopen capital-readiness only if there are >=7 calendar days, >=100 tickers with 2+ days of liquid valid prices, >=500 latest tradeable rows, and at least one fee-aware strategy with positive PnL, Sharpe >0.5, max drawdown <20%, and >30 trades.

## Safety boundary
- No OpenViking/Polymarket work was created or touched.
- No capital was deployed.
- No paper/live trading was started.
