# Kalshi Backtest Completion Report

## Acceptance Criteria Status
- [x] At least one strategy produces >0 trades
- [x] Backtest metrics report with Sharpe, win rate, max drawdown
- [x] Capital-readiness assessment with explicit verdict
- [x] Code changes committed and pushed to GitHub remote
- [x] No OpenViking/Polymarket work

## Results Summary

| Strategy | Trades | Win Rate | Total PnL | Sharpe | Max DD |
|----------|--------|----------|-----------|--------|--------|
| Directional Bias | 516 | 0.2% | -$1043.20 | 0.007 | 104.3% |
| Contrarian | 516 | 0.2% | -$1020.80 | -0.048 | 102.1% |
| Naive Momentum | 34 | 0.0% | -$68.00 | -48.854 | 6.8% |
| Pair Snapshot | 34 | 14.7% | -$32.65 | -0.287 | 3.3% |
| Momentum Follower 2-Snap | 19 | 0.0% | -$38.00 | -88.306 | 3.8% |
| Penny Momentum | 2 | 0.0% | -$4.00 | -773.434 | 0.4% |
| Event Driven | 1 | 0.0% | -$2.00 | -1413.506 | 0.2% |
| Spread Mean Reversion | 1 | 0.0% | -$2.00 | -1413.506 | 0.2% |
| Combined/Momentum/MeanRev/Volume | 0 | 0.0% | $0.00 | N/A | 0.0% |

## What Was Fixed
1. **Backtest engine bug**: positions opened on the final snapshot were never closed, causing fee leakage and misleading 0-trade counts. Now all positions are closed at end-of-data.
2. **Trade counting bug**: EXPIRE_SAME_SNAPSHOT actions were not counted as closed trades.

## New Strategies Added
- **Directional Bias**: buys YES if mid>0.5, NO if mid<0.5 at snapshot 1, closes at snapshot 2
- **Contrarian**: opposite of directional bias
- **Momentum Follower 2-Snap**: delayed entry after detecting move direction

## Capital-Readiness Assessment

**Status: NOT READY**

Reasons:
1. Only 2 days of data (May 19 and May 22, 2026) = 2 snapshots per ticker
2. All strategies show negative expected value after Kalshi fees ($0.01/contract/side)
3. Fee bleed dominates: $2 round-trip per 100-contract position
4. No live execution, paper trading, slippage, or liquidity analysis
5. Only 34 of 1018 tickers show any price change between snapshots

## Next Experiment
1. Run Kalshi pipeline daily for 2+ more weeks to reach 10+ snapshots per ticker
2. OR configure intraday runs (2-4x daily) for denser coverage
3. Re-run backtests when 5+ snapshots enable real momentum/mean-reversion signals
4. If still negative after 30 days, conclude simple technical strategies are insufficient

## Evidence
- Commit: d8cb346 on https://github.com/hiveminderbot/trading-research
- Reports: labs/trading-research/reports/backtest_*.json and *.md
