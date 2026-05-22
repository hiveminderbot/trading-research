# Kalshi Trading Strategy — Capital-Readiness Assessment

**Date:** 2026-05-22  
**Assessor:** autonomy-worker  
**Status:** **NOT READY** — Data insufficient for valid backtest

---

## Executive Summary

The Kalshi signal extraction and backtest pipeline has been built and validated as an **internal capability** (Tier 1). However, it is **not capital-ready** because the historical dataset lacks the minimum time-series depth required to produce statistically meaningful backtest results.

**Verdict:** Do not deploy capital. Continue data accumulation with the fixed pipeline.

---

## 1. Pipeline Status

| Component | Status | Evidence |
|-----------|--------|----------|
| Data ingestion | **Fixed** | Bulk `/markets` endpoint now used instead of per-series fetches |
| Price data quality | **Good** | 1,043 financial markets with valid `yes_bid_dollars` / `yes_ask_dollars` |
| Signal generation | **Functional** | Momentum, mean reversion, and combined strategies implemented |
| Backtest engine | **Functional** | Zero trades produced due to insufficient time-series depth |
| Live execution | **Not built** | No Kalshi API key or order placement logic |

---

## 2. Data Inventory

### Total Records
- **40,468** total market snapshots in database
- **1,064** snapshots with valid prices (`yes_bid` IS NOT NULL)
- **7** pipeline runs recorded

### Time-Series Depth (The Blocker)

| Date | Records | With Prices | Tickers with 2+ Snapshots |
|------|---------|-------------|---------------------------|
| 2026-05-19 | 15,427 | 0 | 0 |
| 2026-05-22 | 25,041 | 1,064 | **0** |

**Critical finding:** Zero tickers have 2 or more snapshots **with prices**.

The backtest engine requires at least 2 price observations per ticker to compute:
- `momentum_3` — 3-period price velocity
- `mean_reversion` — deviation from rolling mean
- `signal_score` — composite signal for entry/exit

Without 2+ snapshots, no signals are generated, and **zero trades are produced**.

### Root Cause Analysis

1. **May 19 data (runs 1–4):** Fetched via per-series API calls. The `normalize_market()` function had a field-mapping bug — it looked for `yes_bid` (which does not exist in the batch `/markets` response) and fell back to `yes_bid_dollars`, but the per-series endpoint was returning data without price fields for most markets. Result: 15,427 records with `NULL` prices.

2. **May 22 early data (runs 5–6):** Severe rate limiting (HTTP 429) blocked the per-series fetcher. Only 20–40 markets were successfully fetched per run. Result: 40 records with valid prices, but no ticker overlap with the new bulk fetch.

3. **May 22 bulk fetch (run 8, this session):** Used the bulk `/markets?limit=1000` endpoint with pagination. Successfully fetched 20,000 markets and stored 1,043 financial markets with valid prices. Result: **single snapshot only** — no time-series depth yet.

---

## 3. Backtest Results (All Strategies)

| Strategy | Total Trades | Win Rate | Total PnL | Sharpe | Max DD |
|----------|-------------|----------|-----------|--------|--------|
| Momentum | 0 | N/A | $0.00 | N/A | 0% |
| Mean Reversion | 0 | N/A | $0.00 | N/A | 0% |
| Combined | 0 | N/A | $0.00 | N/A | 0% |

**Interpretation:** Zero trades is the *correct* output given the data. The engine is working; the data is not.

---

## 4. Capital-Readiness Checklist

| Requirement | Status | Blocker |
|-------------|--------|---------|
| ≥30 days of daily snapshots | ❌ NOT MET | Only 1 day of price data |
| ≥100 tickers with 2+ snapshots | ❌ NOT MET | 0 tickers meet threshold |
| Backtest produces >50 trades | ❌ NOT MET | 0 trades |
| Positive expected value (Sharpe > 0.5) | ❌ NOT MET | Cannot compute |
| Live API order placement tested | ❌ NOT MET | No API key or execution module |
| Fee-adjusted PnL | ❌ NOT MET | No trade history to adjust |
| Risk controls (position sizing, stops) | ❌ NOT MET | Not implemented |

---

## 5. Timeline to Capital-Readiness

### Phase 1: Data Accumulation (Days 1–30)
- **Action:** Run the fixed bulk-fetch daily runner once per day.
- **Expected outcome:** 30 snapshots per ticker for active financial markets.
- **Validation:** Weekly check: `SELECT COUNT(DISTINCT ticker) FROM market_snapshots WHERE yes_bid IS NOT NULL GROUP BY ticker HAVING COUNT(*) >= 2`

### Phase 2: Backtest Validation (Day 30)
- **Action:** Re-run all three strategies on 30-day dataset.
- **Minimum viable metrics:**
  - ≥100 tickers with 2+ snapshots
  - ≥50 total trades across all strategies
  - Win rate > 50% OR positive total PnL
  - Sharpe ratio > 0.5

### Phase 3: Paper Trading (Days 31–60)
- **Action:** Build Kalshi API integration for paper/order placement.
- **Requirements:**
  - Kalshi API key (requires account verification)
  - Order placement with $0.01/contract fee accounting
  - Position tracking and PnL reconciliation
  - Daily report comparing backtest vs. actual fills

### Phase 4: Live Deployment (Day 61+)
- **Action:** Deploy with strict risk controls.
- **Requirements:**
  - Max 1% of capital per trade
  - Stop-loss at -5% per position
  - Daily loss limit at -2% of capital
  - Weekly strategy review and re-calibration

---

## 6. Fixes Applied Today

### Daily Runner Fix
- **Problem:** Per-series fetching caused aggressive rate limiting (429) and incomplete data.
- **Solution:** Replaced with bulk `/markets?limit=1000` paginated fetch.
- **Result:** 20,000 markets fetched in ~10 seconds vs. 847 individual API calls that timed out.
- **Code:** See `kalshi_daily_runner.py` — `fetch_all_markets_bulk()` function added.

### Data Quality Fix
- **Problem:** `normalize_market()` used `yes_bid` (nonexistent in batch response) with fallback to `yes_bid_dollars`, but `safe_float()` was receiving strings like `"0.0500"` which parsed correctly. The real issue was the per-series endpoint not returning price fields.
- **Solution:** Bulk endpoint consistently returns `*_dollars` fields for all markets.

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Kalshi API changes field names | Medium | High | Monitor API changelog; add validation layer |
| Rate limiting on bulk endpoint | Low | Medium | Add exponential backoff; cache results |
| Market liquidity too low for execution | Medium | High | Filter markets by `volume_24h_fp > 1000` |
| Binary contract expiration erodes edge | High | High | Limit holding period to <50% of time to expiry |
| Overfitting to 30-day backtest | Medium | High | Use walk-forward validation; reserve 20% out-of-sample |

---

## 8. Recommendation

**DO NOT deploy capital at this time.**

The pipeline is functional and the data quality issue has been fixed. The next step is **passive data accumulation** for 30 days. No further engineering work is required until Day 30 — the daily runner can run via cron.

**Next review date:** 2026-06-21 (30 days from now).

**Trigger for early review:** If the daily runner fails for 3+ consecutive days, investigate API changes or IP blocks.

---

*Generated by Kalshi Backtest Engine — autonomy-worker*  
*Evidence file attached: `reports/kalshi_capital_readiness_assessment_2026-05-22.md`*
