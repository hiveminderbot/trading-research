# Kalshi Readiness Diagnostic — 2026-05-24

**Capital-readiness verdict:** **NOT READY**

## Latest pipeline run

- Run: `2026-05-24T00:00:00+00:00`
- Markets fetched: 46511
- New records: 0
- Changed prices: 653
- Error: None
- Latest valid-bid rows: 653
- Latest tradeable/liquid rows (`bid>0`, `volume>0`, `OI>0`): 212

## Data coverage

- Valid-price tickers with 2+ calendar days: 599
- Valid-price tickers with 3+ calendar days: 0
- Valid-price tickers with 2+ snapshots: 641
- Valid-price tickers with 4+ snapshots: 621

### Per-day coverage

| Day | Rows | Tickers | Valid bid rows | Tradeable rows |
|---|---:|---:|---:|---:|
| 2026-05-19 | 15427 | 12430 | 0 | 0 |
| 2026-05-22 | 35908 | 32442 | 36 | 1 |
| 2026-05-23 | 325997 | 46571 | 4402 | 1383 |
| 2026-05-24 | 46511 | 46511 | 653 | 212 |

### Cross-day valid-price ticker overlap

| Day A | Day B | Overlap |
|---|---|---:|
| 2026-05-23 | 2026-05-24 | 599 |

## Backtest summary

| Strategy | Period | Trades | Win rate | PnL | Sharpe | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-24 | 4 | 0.0 | -32.5 | -0.7986 | 0.0325 |
| Contrarian | 2026-05-19→2026-05-19 | 516 | 0.0019 | -1020.8 | -0.0479 | 1.0208 |
| Contrarian | 2026-05-19→2026-05-24 | 619 | 0.0372 | -1206.8 | 0.0052 | 1.2068 |
| Directional Bias | 2026-05-19→2026-05-19 | 516 | 0.0019 | -1043.2 | 0.0068 | 1.0432 |
| Directional Bias | 2026-05-19→2026-05-24 | 619 | 0.0452 | -1269.2 | -0.0263 | 1.2692 |
| Event Driven | 2026-05-19→2026-05-19 | 1 | 0.0 | -2.0 | -1413.5065 | 0.002 |
| Event Driven | 2026-05-19→2026-05-24 | 150 | 0.0133 | -482.0 | -0.5273 | 0.482 |
| Mean Reversion Strategy | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Mean Reversion Strategy | 2026-05-19→2026-05-24 | 47 | 0.1277 | -26.0 | -0.0687 | 0.063 |
| Momentum Follower 2-Snap | 2026-05-19→2026-05-19 | 19 | 0.0 | -38.0 | -88.3063 | 0.038 |
| Momentum Follower 2-Snap | 2026-05-19→2026-05-24 | 371 | 0.0728 | -941.0 | -0.38 | 0.941 |
| Momentum Strategy | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Momentum Strategy | 2026-05-19→2026-05-24 | 24 | 0.0417 | -163.5 | -0.4364 | 0.1635 |
| Naive Momentum | 2026-05-19→2026-05-19 | 34 | 0.0 | -68.0 | -48.8538 | 0.068 |
| Naive Momentum | 2026-05-19→2026-05-24 | 680 | 0.0603 | -1611.5 | 0.0271 | 1.6115 |
| Pair Snapshot | 2026-05-19→2026-05-19 | 34 | 0.1471 | -32.65 | -0.2866 | 0.0333 |
| Pair Snapshot | 2026-05-19→2026-05-24 | 158 | 0.3924 | -346.65 | -0.0726 | 0.4011 |
| Penny Momentum | 2026-05-19→2026-05-19 | 2 | 0.0 | -4.0 | -773.4338 | 0.004 |
| Penny Momentum | 2026-05-19→2026-05-24 | 214 | 0.1589 | -835.0 | -0.2515 | 0.847 |
| Spread Mean Reversion | 2026-05-19→2026-05-19 | 1 | 0.0 | -2.0 | -1413.5065 | 0.002 |
| Spread Mean Reversion | 2026-05-19→2026-05-24 | 88 | 0.2614 | -159.0 | -0.1129 | 0.214 |
| Volume Breakout | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Volume Breakout | 2026-05-19→2026-05-24 | 33 | 0.1212 | 45.0 | 0.0675 | 0.0517 |

## Recommendation

- Latest run has 212 tradeable/liquid rows; target >=500 for broad backtest coverage.
- Positive PnL exists but fails risk-adjusted gates (Sharpe >0.5 and max drawdown <20% required): Volume Breakout (PnL=45.0, Sharpe=0.0675, maxDD=0.0517).
- Do **not** deploy capital or paper-trade this as a candidate strategy yet; current evidence is data accumulation plus backtests that fail the risk-adjusted go/no-go gates.
- Continue daily snapshots until the 7-day gate, then re-run the same diagnostic and fee-aware backtests.

## Evidence files

- JSON: `reports/kalshi_readiness_2026-05-24.json`
- Markdown: `reports/kalshi_readiness_2026-05-24.md`
