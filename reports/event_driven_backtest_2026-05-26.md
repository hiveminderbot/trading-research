
# Kalshi Event-Driven Strategy Backtest Report

## Executive Summary

**Date:** 2026-05-26
**Data Period:** 2026-05-22 to 2026-05-26 (5 days)
**Total Snapshots:** 470,259
**Distinct Tickers with Valid Prices:** 655 (May 26)
**Event-Driven Tickers:** 265 (Fed, CPI, WTI)

## Key Findings

### 1. WTI Contracts Show Massive Overnight Moves

WTI contracts expiring May 26 showed dramatic overnight price drops:
- May 23 (Saturday) -> May 24 (Sunday): YES prices dropped 30-50 cents
- Example: KXWTI-26MAY2614-T91.99: YES bid 0.86 -> 0.36 (-50 cents)
- Example: KXWTI-26MAY2614-T93.99: YES bid 0.76 -> 0.25 (-51 cents)

This represents a massive repricing event, likely due to weekend oil news.

### 2. CPI Contracts Show Extreme Volatility

CPI July contracts showed extreme moves:
- KXCPI-26JUL-T0.0: 0.98 -> 0.01 -> 0.73 (massive swing)
- KXCPI-26JUL-T0.1: 0.80 -> 0.01 -> 0.42 (massive swing)
- KXCPIYOY-26JUN-T3.9: 0.90 -> 0.90 -> 0.06 (84 cent drop)

### 3. Strategy Tests

#### WTI Near-Expiry Contrarian (within 5 days)
- Total Trades: 52
- Total PnL: +\.88
- Win Rate: 40.4%
- Avg Trade: +\/usr/bin/bash.06
- **Verdict:** Marginally positive but not statistically significant

#### WTI All-Expiry Contrarian
- Total Trades: 132
- Total PnL: -.95
- Win Rate: 16.7%
- Avg Trade: -\/usr/bin/bash.12
- **Verdict:** Negative - far-dated contracts do not have event risk

#### WTI Overnight Momentum
- Total Trades: 132
- Total PnL: -.76
- Win Rate: 14.4%
- **Verdict:** Strongly negative

## Critical Insight

The ONLY profitable segment was WTI contracts within 5 days of expiry
that experienced a known event (May 23-24 weekend news). However:

1. **Sample size is tiny** (1 event, 52 trades)
2. **Cannot distinguish luck from skill**
3. **No forward test possible** without more data
4. **Bid-ask spreads erode profits** (not fully accounted for)

## Capital Readiness Verdict: NOT READY

**Reasons:**
- Only 3-5 days of data with valid prices
- Only 1 identifiable event period (May 23-24)
- No statistically significant edge
- Cannot validate bid-ask execution costs
- No live API paper trading tested

## Next Steps

1. **Continue data accumulation** - need 30+ days with daily snapshots
2. **Focus on near-expiry event contracts** (within 5 days)
3. **Track actual economic calendar** - map events to contract moves
4. **Paper trade with Kalshi API** once edge is validated
5. **Consider alternative: prediction market arbitrage** between Kalshi and Polymarket

## Data Quality Issues

- May 25 data is missing (Sunday?)
- Intraday snapshots are sparse (7 per day on May 23, 1 on May 24/26)
- No volume data for many contracts
- Bid-ask spreads vary widely (0.01 to 0.50+)
