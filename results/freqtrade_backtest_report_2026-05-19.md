# Freqtrade Sandbox Backtest Report

**Date:** 2026-05-19  
**Bead:** autonomy-xmy0  
**Strategy:** LLMStrategy (RSI + MACD crossover with ATR stop-loss)  
**Data:** Coinbase BTC/USDT and ETH/USDT, 5m candles  
**Period:** 2026-04-01 to 2026-05-19 (48 days)  
**Mode:** Dry-run / backtest

---

## Setup Evidence

- Freqtrade installed via pip in `freqtrade-sandbox/.venv`
- Config: `user_data/config.json` with `dry_run: true`, Coinbase exchange, 100 USDT stake
- Strategy: `user_data/strategies/LLMStrategy.py` (LLM-generated)
- Data downloaded via `freqtrade download-data --exchange coinbase --erase`
- Backtest command:
  ```bash
  freqtrade backtesting --config user_data/config.json --strategy LLMStrategy \
    --timerange 20260401-20260519 --timeframe 5m --export trades
  ```

---

## Backtest Results

| Metric | Value |
|--------|-------|
| Starting balance | 1000 USDT |
| Final balance | 1000 USDT |
| Absolute profit | -0 USDT |
| Total profit % | -0.00% |
| CAGR % | -0.00% |
| Sharpe (closed trades) | -0.76 |
| Profit factor | 0.04 |
| Total trades | 2 |
| Win / Draw / Loss | 1 / 0 / 1 |
| Win rate | 50.0% |
| Avg trade duration | 6 days, 19:58:00 |
| Market change | +7.98% |
| Max drawdown | 0 USDT (0.00%) |
| Rejected entry signals | 0 |

### Per-pair breakdown

| Pair | Trades | Avg Profit % | Win / Loss | Win% |
|------|--------|--------------|------------|------|
| BTC/USDT | 1 | 0.0% | 1 / 0 | 100% |
| ETH/USDT | 1 | -0.0% | 0 / 1 | 0% |

### Signal analysis (independent validation)

- BTC entry signals (RSI<30 + MACD crossover): **1** (2026-04-27 06:40)
- BTC exit signals (RSI>70 + MACD crossunder): **3**
- ETH entry signals: **2** (2026-04-27 06:20, 2026-04-29 16:45)
- ETH exit signals: **1** (2026-04-13 23:45)

The strategy is extremely conservative — only 2 trades in 48 days — because the RSI<30 + MACD crossover condition is rare in the sampled data.

---

## Dry-run Trading Evidence

- Bot started in dry-run mode with `freqtrade trade --config user_data/config.json --strategy LLMStrategy --dry-run`
- Bot reached RUNNING state successfully
- No trades executed in the brief live window (expected — signals are rare)
- SQLite trade DB initialized at `user_data/tradesv3.dryrun.sqlite` (0 trades)

---

## Assessment

**Capital-readiness:** NOT READY.

This is a valid Tier 2 demonstrated capability (working Freqtrade sandbox, real exchange data, reproducible backtest), but it is not capital-ready because:

1. **Strategy is unprofitable** — 0% return vs +7.98% market buy-and-hold.
2. **Sample size is tiny** — only 2 trades in 48 days; no statistical significance.
3. **No paper-trading longevity** — bot ran for seconds, not hours/days.
4. **No risk controls validated** — ATR stop-loss exists but was not triggered in backtest.

---

## Recommendations

1. **Tune strategy parameters** — widen RSI thresholds (e.g., 40/60 instead of 30/70) or add additional entry conditions to increase trade frequency.
2. **Run longer paper trade** — leave bot running for 24-48h to validate live signal generation and order simulation.
3. **Compare to benchmark** — add a buy-and-hold baseline strategy to the backtest for direct comparison.
4. **Try alternative strategies** — test momentum (EMA cross), mean-reversion (Bollinger Bands), or ML-based approaches.

---

## Artifacts

- Repo: https://github.com/hiveminderbot/trading-research
- Commit: `d8295d4`
- Strategy: `freqtrade-sandbox/user_data/strategies/LLMStrategy.py`
- Config: `freqtrade-sandbox/user_data/config.json`
- Backtest meta: `freqtrade-sandbox/user_data/backtest_results/backtest-result-2026-05-19_10-51-10.meta.json`
