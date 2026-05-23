# Kalshi Public API Market Data Pipeline

End-to-end data pipeline that fetches active financial markets from Kalshi's public API, normalizes the data, and stores it in SQLite with timestamped snapshots.

## Quick Start

```bash
python3 kalshi_daily_runner.py
```

## Intraday Cron Setup (4x Daily)

The runner supports idempotent intraday execution via canonical 6-hour slots.

### Cron Schedule

Add to your crontab (`crontab -e`):

```bash
# Kalshi intraday data collection — 4x daily UTC
0 0 * * * cd /home/exedev/autonomy/labs/trading-research && python3 kalshi_daily_runner.py
0 6 * * * cd /home/exedev/autonomy/labs/trading-research && python3 kalshi_daily_runner.py
0 12 * * * cd /home/exedev/autonomy/labs/trading-research && python3 kalshi_daily_runner.py
0 18 * * * cd /home/exedev/autonomy/labs/trading-research && python3 kalshi_daily_runner.py
```

### Idempotency

- The runner auto-computes `run_id` from the current 6-hour slot (`00:00`, `06:00`, `12:00`, `18:00` UTC).
- If a `run_id` already exists in `pipeline_runs`, the run is skipped unless `--force` is passed.
- This prevents duplicate records when cron overlaps or restarts.

### Manual Run with Explicit Slot

```bash
python3 kalshi_daily_runner.py --run-id 2026-05-23T12:00:00+00:00
```

### Coverage Report

```bash
python3 kalshi_daily_runner.py --coverage-only
```

## Data Schema

### market_snapshots
| Column | Type | Description |
|--------|------|-------------|
| ticker | TEXT | Market ticker (unique per snapshot) |
| title | TEXT | Market title |
| series_ticker | TEXT | Series ticker (groups related markets) |
| status | TEXT | active, settled, etc. |
| yes_bid | REAL | Yes bid price in dollars |
| yes_ask | REAL | Yes ask price in dollars |
| no_bid | REAL | No bid price in dollars |
| no_ask | REAL | No ask price in dollars |
| volume_fp | REAL | Total volume |
| open_interest | REAL | Open interest |
| expiration_date | TEXT | Market expiration |
| fetched_at | TEXT | ISO timestamp of fetch |

### pipeline_runs
| Column | Type | Description |
|--------|------|-------------|
| run_at | TEXT | ISO timestamp |
| markets_fetched | INTEGER | Markets fetched in run |
| new_records | INTEGER | New records inserted |
| changed_prices | INTEGER | Markets with price changes |
| error | TEXT | Error message if any |

## Validation

Run the pipeline and verify:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('results/kalshi_market_data.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM market_snapshots WHERE fetched_at = (SELECT MAX(fetched_at) FROM market_snapshots)')
print('Latest run records:', c.fetchone()[0])
c.execute('SELECT COUNT(DISTINCT ticker) FROM market_snapshots')
print('Unique markets:', c.fetchone()[0])
conn.close()
"
```

## API Endpoint

- Base: `https://api.elections.kalshi.com/trade-api/v2`
- No authentication required for public market data
- Rate limit: ~5 req/s observed; 429 handled with exponential backoff
