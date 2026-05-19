# Freqtrade Backtest Comparison Report

Date: 2026-05-19

Timerange: 2026-04-20 to 2026-05-19 (29 days)

Exchange: Coinbase (dry-run mode)

Pairs: BTC/USDT, ETH/USDT

---

## Strategy Comparison

| Strategy | Trades | Win Rate | Total Profit % | Total Profit USDT | Sharpe | Max Drawdown % | Avg Duration |
|----------|--------|----------|----------------|-------------------|--------|----------------|--------------|
| **Buy & Hold** | 0 | N/A | **+6.37%** | +63.68 | N/A | N/A | N/A |
| SimpleRSIStrategy | 86 | 0.0% | -20.11% | -201.08 | -115.77 | 20.11% | 7:57:00 |
| LLMStrategy | 267 | 0.0% | -65.52% | -655.19 | -2041.80 | 65.52% | 0:21:00 |
| EMAStrategy | 284 | 1.1% | -68.32% | -683.20 | -880.37 | 68.32% | 2:27:00 |
| **TrendFollowStrategy** | 69 | 1.4% | **-17.00%** | -169.96 | -24.83 | 17.00% | 2:46:00 |
| **RegimeSwitchStrategy** | 117 | 0.0% | **-27.85%** | -278.53 | -39.99 | 27.85% | 2:33:00 |

## Detailed Metrics

### Buy & Hold (Benchmark)

- **Start Price BTC:** $68,195.68 → **End Price:** $76,646.41 (**+12.39%**)
- **Start Price ETH:** $2,103.67 → **End Price:** $2,110.93 (**+0.35%**)
- **Weighted (50/50):** **+6.37%** (+63.68 USDT on $1,000)

### SimpleRSIStrategy

- **Trades:** 86
- **Win Rate:** 0.00%
- **Total Profit:** -20.11% (-201.08 USDT)
- **Sharpe Ratio:** -115.77
- **Max Drawdown:** 20.11% (201.08 USDT)

### LLMStrategy

- **Trades:** 267
- **Win Rate:** 0.00%
- **Total Profit:** -65.52% (-655.19 USDT)
- **Sharpe Ratio:** -2041.80
- **Max Drawdown:** 65.52% (655.19 USDT)

### EMAStrategy

- **Trades:** 284
- **Win Rate:** 1.06%
- **Total Profit:** -68.32% (-683.20 USDT)
- **Sharpe Ratio:** -880.37
- **Max Drawdown:** 68.32% (683.20 USDT)

### TrendFollowStrategy (NEW — EMA cross + ADX > 25)

- **Trades:** 69
- **Win Rate:** 1.45% (1 win / 68 losses)
- **Total Profit:** -17.00% (-169.96 USDT)
- **Sharpe Ratio:** -24.83
- **Max Drawdown:** 17.00% (169.96 USDT)
- **Avg Trade Duration:** 2:46:00

### RegimeSwitchStrategy (NEW — regime detection + adaptive logic)

- **Trades:** 117
- **Win Rate:** 0.00%
- **Total Profit:** -27.85% (-278.53 USDT)
- **Sharpe Ratio:** -39.99
- **Max Drawdown:** 27.85% (278.53 USDT)
- **Avg Trade Duration:** 2:33:00

## Key Findings

1. **All 5 algorithmic strategies are unprofitable** vs buy-and-hold (+6.37%).
2. **TrendFollowStrategy is the best-performing algorithmic strategy** (-17.00%), but still far below buy-and-hold.
3. **RegimeSwitchStrategy performs worse** (-27.85%) despite adaptive logic — regime detection on 5m data is noisy and triggers false signals.
4. **Mean-reversion strategies fail hardest** in this market regime (BTC +12.39% over 29 days).
5. **Fee impact is severe** on short-duration trades. Coinbase worst-case fee of 1.2% per trade erodes profits rapidly.
6. **Win rates are near-zero across all strategies** (0–1.4%), indicating systematic misalignment between signal logic and price action.

## Capital-Readiness Assessment

**NOT READY** — Explicit rejection of all current strategies.

Evidence required for capital-readiness:
- [ ] At least one strategy with positive backtest return vs buy-and-hold
- [ ] Win rate > 50% with meaningful sample size (>100 trades)
- [ ] Sharpe ratio > 0
- [ ] Max drawdown < 20%
- [ ] 24+ hour paper-trading validation with simulated trades

## Recommendations

1. **Pivot to longer timeframes** — Test on 1h or 4h candles to reduce noise and fee impact.
2. **Use Freqtrade hyperopt** — Optimize parameters on 70/30 train/test split instead of hand-tuning.
3. **Test on bear market data** — Download 2022 data to see if mean-reversion works in downtrends.
4. **Consider ML-based approaches** — Freqtrade's FreqAI for adaptive signal generation.
5. **Reduce trade frequency** — Fewer, higher-conviction trades with wider stops.
