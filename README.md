# Kalshi Public API Market Data Pipeline

End-to-end data pipeline that fetches active financial markets from Kalshi's public API, normalizes the data, and stores it in SQLite with timestamped snapshots.

## Quick Start

```bash
python3 kalshi_market_pipeline.py
```

## Data Schema

### market_snapshots
| Column | Type | Description |
|--------|------|-------------|
| ticker | TEXT | Market ticker (unique per snapshot) |
| title | TEXT | Market title |
| event_ticker | TEXT | Event ticker (groups related markets) |
| status | TEXT | active, settled, etc. |
| yes_bid_dollars | REAL | Yes bid price in dollars |
| yes_ask_dollars | REAL | Yes ask price in dollars |
| no_bid_dollars | REAL | No bid price in dollars |
| no_ask_dollars | REAL | No ask price in dollars |
| last_price_dollars | REAL | Last traded price |
| volume_fp | REAL | Total volume |
| volume_24h_fp | REAL | 24h volume |
| open_interest | REAL | Open interest |
| liquidity_dollars | REAL | Liquidity in dollars |
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
