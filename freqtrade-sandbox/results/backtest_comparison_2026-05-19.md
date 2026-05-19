# Freqtrade Backtest Comparison Report

Date: 2026-05-19

Timerange: 2026-04-20 to 2026-05-19 (29 days)

Exchange: Coinbase (dry-run mode)

Pairs: BTC/USDT, ETH/USDT

---

## Strategy Comparison

| Strategy | Trades | Win Rate | Total Profit % | Total Profit USDT | Sharpe | Max Drawdown % | Avg Duration |
|----------|--------|----------|----------------|-------------------|--------|----------------|--------------|
| LLMStrategy | 267 | 0.0% | -65.52% | -655.19 | -2041.80 | 65.52% | 0:21:00 |

| EMAStrategy | 284 | 1.1% | -68.32% | -683.20 | -880.37 | 68.32% | 2:27:00 |

| SimpleRSIStrategy | 86 | 0.0% | -20.11% | -201.08 | -115.77 | 20.11% | 7:57:00 |

## Detailed Metrics

### LLMStrategy

- **Trades:** 267
- **Win Rate:** 0.00%
- **Total Profit:** -65.52% (-655.19 USDT)
- **Sharpe Ratio:** -2041.80
- **Sortino Ratio:** -2041.80
- **Calmar Ratio:** -65.88
- **SQN:** -189.32
- **Profit Factor:** 0.00
- **Expectancy:** -2.45
- **Max Drawdown:** 65.52% (655.19 USDT)
- **Avg Trade Duration:** 0:21:00
- **CAGR:** -100.00%
- **Avg Stake:** 100.00 USDT
- **Market Change:** -1.13%

### EMAStrategy

- **Trades:** 284
- **Win Rate:** 1.06%
- **Total Profit:** -68.32% (-683.20 USDT)
- **Sharpe Ratio:** -880.37
- **Sortino Ratio:** -1018.38
- **Calmar Ratio:** -65.88
- **SQN:** -79.16
- **Profit Factor:** 0.00
- **Expectancy:** -2.41
- **Max Drawdown:** 68.32% (683.20 USDT)
- **Avg Trade Duration:** 2:27:00
- **CAGR:** -100.00%
- **Avg Stake:** 100.00 USDT
- **Market Change:** -1.13%

### SimpleRSIStrategy

- **Trades:** 86
- **Win Rate:** 0.00%
- **Total Profit:** -20.11% (-201.08 USDT)
- **Sharpe Ratio:** -115.77
- **Sortino Ratio:** -115.77
- **Calmar Ratio:** -65.88
- **SQN:** -18.84
- **Profit Factor:** 0.00
- **Expectancy:** -2.34
- **Max Drawdown:** 20.11% (201.08 USDT)
- **Avg Trade Duration:** 7:57:00
- **CAGR:** -94.07%
- **Avg Stake:** 100.00 USDT
- **Market Change:** -1.13%

## Observations

1. **All strategies are unprofitable** on this 29-day period with Coinbase data.
2. **SimpleRSIStrategy** has the smallest losses (-20.11%) but still 0% win rate.
3. **EMAStrategy** has slightly worse performance (-68.32%) with 1.1% win rate (3 wins out of 284 trades).
4. **LLMStrategy** (Bollinger Bands + RSI + ATR) performs poorly (-65.52%) with 0% win rate.
5. The market change over the period was only -1.13%, so the losses are primarily due to strategy logic and fees.
6. **Fee impact:** Coinbase worst-case fee of 1.2% per trade significantly erodes profits on short-duration trades.
7. **Recommendation:** These mean-reversion strategies are not viable with current parameters on this dataset.
   - Consider trend-following instead of mean-reversion in this market regime.
   - Reduce trade frequency to minimize fee impact.
   - Test on longer timeframes (1h, 4h) instead of 5m.
   - Add market regime filter (e.g., ADX) to avoid trading in choppy conditions.
