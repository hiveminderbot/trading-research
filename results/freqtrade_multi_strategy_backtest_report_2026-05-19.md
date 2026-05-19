# Freqtrade Multi-Strategy Backtest Report

**Date:** 2026-05-19
**Bead:** autonomy-xmy0
**Data:** Coinbase BTC/USDT and ETH/USDT, 5m candles
**Period:** 2026-04-01 to 2026-05-19 (48 days)
**Mode:** Dry-run / backtest

---

## Setup Evidence

- Freqtrade installed via pip in `freqtrade-sandbox/.venv`
- Config: `user_data/config.json` with `dry_run: true`, Coinbase exchange, 100 USDT stake
- Data downloaded via `freqtrade download-data --exchange coinbase --erase`
- All strategies committed and pushed to GitHub remote

---

## Strategy Comparison

| Strategy | Description | Trades | Win Rate | Total Profit % | Max Drawdown | Sharpe |
|----------|-------------|--------|----------|----------------|--------------|--------|
| **Buy & Hold** | Split $500 BTC + $500 ETH, hold 48 days | 0 | N/A | **+6.37%** | N/A | N/A |
| TrendFollowStrategy | EMA 9/21 crossover + ADX > 25 + RSI > 50 | 107 | 2.8% | **-25.07%** | 25.07% | -23.17 |
| RegimeSwitchStrategy | ADX regime detection (trend vs range) | 190 | 0.0% | **-44.91%** | 44.91% | -39.45 |
| SimpleRSIStrategy | RSI < 30 entry, RSI > 70 exit | 134 | 0.7% | **-31.48%** | 31.48% | -107.12 |
| EMAStrategy | EMA 9/21 crossover + RSI filter | 377 | 1.9% | **-90.13%** | 90.13% | -561.68 |
| LLMStrategy | Bollinger Bands mean reversion + RSI + ATR stop | 369 | 0.0% | **-90.16%** | 90.16% | -1493.05 |

### Buy & Hold Benchmark (calculated independently)

| Pair | Start Price | End Price | Return |
|------|-------------|-----------|--------|
| BTC/USDT | $68,195.68 | $76,646.41 | **+12.39%** |
| ETH/USDT | $2,103.67 | $2,110.93 | **+0.35%** |
| **Weighted (50/50)** | — | — | **+6.37%** |

---

## Key Findings

1. **All LLM-generated strategies are unprofitable** vs buy-and-hold
   - Best performing strategy (TrendFollow) lost -25.07% vs +6.37% benchmark
   - Worst performing (LLMStrategy) lost ~-90%

2. **Trend-following also fails on this timerange**
   - TrendFollowStrategy: 107 trades, 2.8% win rate, -25.07% return
   - ADX filter does not prevent losses in choppy bull market

3. **Regime detection fails**
   - RegimeSwitchStrategy: 190 trades, 0% win rate, -44.91% return
   - Regime labels may be lagging or incorrectly calibrated

4. **Mean-reversion strategies fail in bull markets**
   - BTC gained +12.39% over the period
   - Strategies that short/bet against momentum get run over

5. **High trade frequency != profitability**
   - EMAStrategy made 377 trades (8.02/day) with 1.9% win rate
   - More trades = more fees, more losses

---

## Strategy Code Quality

All strategies are syntactically valid and run without errors:
- LLMStrategy.py -- Bollinger Bands + RSI + ATR stop-loss
- EMAStrategy.py -- EMA 9/21 crossover + RSI filter
- SimpleRSIStrategy.py -- Pure RSI mean reversion
- TrendFollowStrategy.py -- EMA crossover + ADX trend filter
- RegimeSwitchStrategy.py -- Market regime detection
- BuyHoldStrategy.py -- Benchmark (synthetic)

---

## Capital-Readiness Assessment

**NOT READY** -- Explicit rejection of all current strategies.

Evidence required for capital-readiness:
- At least one strategy with positive backtest return vs buy-and-hold
- Win rate > 50% with meaningful sample size (>100 trades)
- Sharpe ratio > 0
- Max drawdown < 20%
- 24+ hour paper-trading validation with simulated trades

---

## Recommendations

1. **Test on bear market data** -- Download 2022 data to see if mean-reversion works there
2. **Use Freqtrade hyperopt** -- Optimize parameters on 70/30 train/test split
3. **Consider FreqAI ML-based adaptive signals** -- Instead of hand-coded rules
4. **Evaluate timeframe** -- 5m may be too noisy; try 1h or 4h
5. **Reconsider viability** -- Crypto TA strategies may not be viable for this autonomy lab

---

## Artifacts

- Repo: https://github.com/hiveminderbot/trading-research
- Commit: ce23417
- Strategies: freqtrade-sandbox/user_data/strategies/
- Benchmark calc: freqtrade-sandbox/calc_benchmark.py
