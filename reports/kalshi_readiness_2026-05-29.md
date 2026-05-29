# Kalshi Readiness Diagnostic — 2026-05-29

**Capital-readiness verdict:** **NOT READY**

## Latest pipeline run

- Run: `2026-05-29T06:00:00+00:00`
- Markets fetched: 46491
- New records: 46491
- Changed prices: 8465
- Error: None
- Latest valid-bid rows: 597
- Latest tradeable/liquid rows (`bid>0`, `volume>0`, `OI>0`): 174

## Data coverage

- Valid-price tickers with 2+ calendar days: 627
- Valid-price tickers with 3+ calendar days: 610
- Valid-price tickers with 2+ snapshots: 704
- Valid-price tickers with 4+ snapshots: 658

### Per-day coverage

| Day | Rows | Tickers | Valid bid rows | Tradeable rows |
|---|---:|---:|---:|---:|
| 2026-05-19 | 15427 | 12430 | 0 | 0 |
| 2026-05-22 | 35908 | 32442 | 36 | 1 |
| 2026-05-23 | 325997 | 46571 | 4402 | 1383 |
| 2026-05-24 | 46511 | 46511 | 653 | 212 |
| 2026-05-26 | 232035 | 52630 | 3216 | 947 |
| 2026-05-29 | 46491 | 46491 | 597 | 174 |

### Cross-day valid-price ticker overlap

| Day A | Day B | Overlap |
|---|---|---:|
| 2026-05-23 | 2026-05-24 | 599 |
| 2026-05-23 | 2026-05-26 | 600 |
| 2026-05-23 | 2026-05-29 | 548 |
| 2026-05-24 | 2026-05-26 | 619 |
| 2026-05-24 | 2026-05-29 | 555 |
| 2026-05-26 | 2026-05-29 | 558 |

## Backtest summary

| Strategy | Period | Trades | Win rate | PnL | Sharpe | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-24 | 4 | 0.0 | -32.5 | -0.7986 | 0.0325 |
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-24 | 4 | 0.0 | -169.3554 | -2.3739 | 0.1694 |
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-26 | 6 | 0.1667 | -297.8593 | -1.5233 | 0.2979 |
| Combined Momentum+MeanReversion | 2026-05-19→2026-05-26 | 10 | 0.1 | -198.4604 | -1.0231 | 0.1985 |
| None | None→None | None | None | None | None | None |
| None | None→None | None | None | None | None | None |
| Contrarian | 2026-05-19→2026-05-19 | 516 | 0.0019 | -1020.8 | -0.0479 | 1.0208 |
| Contrarian | 2026-05-19→2026-05-24 | 619 | 0.0372 | -1206.8 | 0.0052 | 1.2068 |
| Contrarian | 2026-05-19→2026-05-26 | 636 | 0.0094 | -22686.5874 | 0.0284 | 22.6866 |
| Contrarian | 2026-05-19→2026-05-26 | 645 | 0.0186 | -11200.5034 | 0.0329 | 11.2005 |
| Directional Bias | 2026-05-19→2026-05-19 | 516 | 0.0019 | -1043.2 | 0.0068 | 1.0432 |
| Directional Bias | 2026-05-19→2026-05-24 | 619 | 0.0452 | -1269.2 | -0.0263 | 1.2692 |
| Directional Bias | 2026-05-19→2026-05-26 | 636 | 0.0173 | -3894.9372 | 0.0137 | 3.8949 |
| Directional Bias | 2026-05-19→2026-05-26 | 645 | 0.0403 | -1684.4284 | -0.0216 | 1.6844 |
| Event Driven | 2026-05-19→2026-05-19 | 1 | 0.0 | -2.0 | -1413.5065 | 0.002 |
| Event Driven | 2026-05-19→2026-05-24 | 150 | 0.0133 | -482.0 | -0.5273 | 0.482 |
| Event Driven | 2026-05-19→2026-05-26 | 202 | 0.0594 | -2725.3575 | -0.0462 | 2.7254 |
| Event Driven | 2026-05-19→2026-05-26 | 281 | 0.1068 | -1991.1047 | 0.0472 | 1.9911 |
| Mean Reversion Strategy | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Mean Reversion Strategy | 2026-05-19→2026-05-24 | 47 | 0.1277 | -26.0 | -0.0687 | 0.063 |
| Mean Reversion Strategy | 2026-05-19→2026-05-24 | 47 | 0.1277 | -446.1836 | -0.4627 | 0.4462 |
| Mean Reversion Strategy | 2026-05-19→2026-05-26 | 93 | 0.1613 | -2804.7105 | -0.0887 | 2.8047 |
| Mean Reversion Strategy | 2026-05-19→2026-05-26 | 141 | 0.234 | -1683.8154 | -0.0472 | 1.7133 |
| Momentum Follower 2-Snap | 2026-05-19→2026-05-19 | 19 | 0.0 | -38.0 | -88.3063 | 0.038 |
| Momentum Follower 2-Snap | 2026-05-19→2026-05-24 | 371 | 0.0728 | -941.0 | -0.38 | 0.941 |
| Momentum Follower 2-Snap | 2026-05-19→2026-05-26 | 469 | 0.0384 | -8140.7387 | 0.0369 | 8.1407 |
| Momentum Follower 2-Snap | 2026-05-19→2026-05-26 | 612 | 0.1242 | -4872.299 | -0.0076 | 4.8723 |
| Momentum Strategy | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Momentum Strategy | 2026-05-19→2026-05-24 | 24 | 0.0417 | -163.5 | -0.4364 | 0.1635 |
| Momentum Strategy | 2026-05-19→2026-05-24 | 24 | 0.0417 | -930.8526 | -0.8917 | 0.9309 |
| Momentum Strategy | 2026-05-19→2026-05-26 | 43 | 0.0698 | -1536.7332 | -0.0669 | 1.5367 |
| Momentum Strategy | 2026-05-19→2026-05-26 | 87 | 0.092 | -1456.6152 | 0.0418 | 1.4566 |
| Naive Momentum | 2026-05-19→2026-05-19 | 34 | 0.0 | -68.0 | -48.8538 | 0.068 |
| Naive Momentum | 2026-05-19→2026-05-24 | 680 | 0.0603 | -1611.5 | 0.0271 | 1.6115 |
| Naive Momentum | 2026-05-19→2026-05-26 | 902 | 0.0355 | -22247.5205 | 0.0034 | 22.2475 |
| Naive Momentum | 2026-05-19→2026-05-26 | 1203 | 0.1031 | -13558.6839 | -0.0178 | 13.5587 |
| Pair Snapshot | 2026-05-19→2026-05-19 | 34 | 0.1471 | -32.65 | -0.2866 | 0.0333 |
| Pair Snapshot | 2026-05-19→2026-05-24 | 158 | 0.3924 | -346.65 | -0.0726 | 0.4011 |
| Pair Snapshot | 2026-05-19→2026-05-26 | 201 | 0.1592 | -6949.4805 | 0.0264 | 6.9495 |
| Pair Snapshot | 2026-05-19→2026-05-26 | 213 | 0.3146 | -3578.6853 | 0.0598 | 3.579 |
| Penny Momentum | 2026-05-19→2026-05-19 | 2 | 0.0 | -4.0 | -773.4338 | 0.004 |
| Penny Momentum | 2026-05-19→2026-05-24 | 214 | 0.1589 | -835.0 | -0.2515 | 0.847 |
| Penny Momentum | 2026-05-19→2026-05-26 | 297 | 0.0909 | -5388.2104 | 0.0186 | 5.3882 |
| Penny Momentum | 2026-05-19→2026-05-26 | 363 | 0.1625 | -3185.1637 | -0.0139 | 3.1864 |
| Spread Mean Reversion | 2026-05-19→2026-05-19 | 1 | 0.0 | -2.0 | -1413.5065 | 0.002 |
| Spread Mean Reversion | 2026-05-19→2026-05-24 | 88 | 0.2614 | -159.0 | -0.1129 | 0.214 |
| Spread Mean Reversion | 2026-05-19→2026-05-26 | 133 | 0.1353 | -2472.5863 | 0.0576 | 2.4726 |
| Spread Mean Reversion | 2026-05-19→2026-05-26 | 181 | 0.1934 | -1979.8351 | -0.0136 | 1.9552 |
| Volume Breakout | 2026-05-19→2026-05-19 | 0 | 0.0 | 0.0 | None | 0.0 |
| Volume Breakout | 2026-05-19→2026-05-24 | 33 | 0.1212 | 45.0 | 0.0675 | 0.0517 |
| Volume Breakout | 2026-05-19→2026-05-26 | 65 | 0.2154 | -988.4493 | -0.4883 | 0.9884 |
| Volume Breakout | 2026-05-19→2026-05-26 | 87 | 0.2759 | -556.1574 | -0.2636 | 0.5643 |

## Recommendation

- Latest run has 174 tradeable/liquid rows; target >=500 for broad backtest coverage.
- Positive PnL exists but fails risk-adjusted gates (Sharpe >0.5 and max drawdown <20% required): Volume Breakout (PnL=45.0, Sharpe=0.0675, maxDD=0.0517).
- Do **not** deploy capital or paper-trade this as a candidate strategy yet; current evidence is data accumulation plus backtests that fail the risk-adjusted go/no-go gates.
- Continue daily snapshots until the 7-day gate, then re-run the same diagnostic and fee-aware backtests.

## Evidence files

- JSON: `reports/kalshi_readiness_2026-05-29.json`
- Markdown: `reports/kalshi_readiness_2026-05-29.md`
