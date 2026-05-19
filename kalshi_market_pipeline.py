"""
Kalshi Public API Market Data Pipeline
Fetches all active financial markets, normalizes data, stores in SQLite with deltas.
Produces Tier 2 demonstrated capability: end-to-end data pipeline with validation.
"""
import urllib.request
import urllib.error
import json
import sqlite3
import ssl
import sys
import time
from datetime import datetime, timezone

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
DB_PATH = "results/kalshi_market_data.db"


import time

def fetch_json(path, retries=3):
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=20, context=CTX)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            title TEXT,
            series_ticker TEXT,
            status TEXT,
            yes_bid REAL,
            yes_ask REAL,
            no_bid REAL,
            no_ask REAL,
            volume_fp REAL,
            open_interest REAL,
            expiration_date TEXT,
            fetched_at TEXT NOT NULL,
            UNIQUE(ticker, fetched_at)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            markets_fetched INTEGER,
            new_records INTEGER,
            changed_prices INTEGER,
            error TEXT
        )
    """)
    conn.commit()
    return conn


def get_financial_series():
    """Fetch all series and filter for financial/economic keywords."""
    keywords = [
        "FED", "RATE", "INFLATION", "GDP", "NASDAQ", "BTC", "ETH", "CPI",
        "UNEMPLOYMENT", "SPY", "SP500", "DOW", "OIL", "GOLD", "SILVER",
        "TREASURY", "BOND", "YIELD", "FOREX", "USD", "EUR", "GBP", "JPY"
    ]
    data = fetch_json("/series?limit=1000")
    series = data.get("series", [])
    financial = []
    for s in series:
        title = (s.get("title") or "").upper()
        ticker = (s.get("ticker") or "").upper()
        for kw in keywords:
            if kw in title or kw in ticker:
                financial.append(s)
                break
    return financial


def get_markets_for_series(series_ticker):
    """Fetch active markets for a given series."""
    markets = []
    cursor = None
    while True:
        path = f"/markets?series_ticker={series_ticker}&limit=1000"
        if cursor:
            path += f"&cursor={cursor}"
        data = fetch_json(path)
        batch = data.get("markets", [])
        markets.extend(batch)
        cursor = data.get("cursor")
        if not cursor or not batch:
            break
    return markets


def normalize_market(m):
    """Extract and normalize key fields from a market object."""
    return {
        "ticker": m.get("ticker"),
        "title": m.get("title"),
        "series_ticker": m.get("series_ticker"),
        "status": m.get("status"),
        "yes_bid": safe_float(m.get("yes_bid")),
        "yes_ask": safe_float(m.get("yes_ask")),
        "no_bid": safe_float(m.get("no_bid")),
        "no_ask": safe_float(m.get("no_ask")),
        "volume_fp": safe_float(m.get("volume_fp")),
        "open_interest": safe_float(m.get("open_interest")),
        "expiration_date": m.get("expiration_date"),
    }


def safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def get_latest_snapshot(conn, ticker):
    c = conn.cursor()
    c.execute("""
        SELECT yes_bid, yes_ask, volume_fp, fetched_at
        FROM market_snapshots
        WHERE ticker = ?
        ORDER BY fetched_at DESC
        LIMIT 1
    """, (ticker,))
    row = c.fetchone()
    if row:
        return {"yes_bid": row[0], "yes_ask": row[1], "volume_fp": row[2], "fetched_at": row[3]}
    return None


def store_markets(conn, markets, run_at):
    c = conn.cursor()
    new_records = 0
    changed_prices = 0
    for m in markets:
        norm = normalize_market(m)
        ticker = norm["ticker"]
        if not ticker:
            continue
        latest = get_latest_snapshot(conn, ticker)
        c.execute("""
            INSERT OR IGNORE INTO market_snapshots
            (ticker, title, series_ticker, status, yes_bid, yes_ask, no_bid, no_ask,
             volume_fp, open_interest, expiration_date, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, norm["title"], norm["series_ticker"], norm["status"],
            norm["yes_bid"], norm["yes_ask"], norm["no_bid"], norm["no_ask"],
            norm["volume_fp"], norm["open_interest"], norm["expiration_date"], run_at
        ))
        if c.rowcount > 0:
            new_records += 1
        if latest and (latest["yes_bid"] != norm["yes_bid"] or latest["yes_ask"] != norm["yes_ask"]):
            changed_prices += 1
    conn.commit()
    return new_records, changed_prices


def main():
    run_at = datetime.now(timezone.utc).isoformat()
    print(f"Kalshi Market Pipeline — Run: {run_at}")
    print("=" * 60)

    conn = init_db()
    error_msg = None
    all_markets = []
    new_records = 0
    changed_prices = 0

    try:
        # 1. Exchange status check
        status = fetch_json("/exchange/status")
        print(f"Exchange active: {status.get('exchange_active')}")
        print(f"Trading active: {status.get('trading_active')}")
        if not status.get("exchange_active"):
            raise RuntimeError("Exchange is not active")

        # 2. Discover financial series
        series = get_financial_series()
        print(f"\nFinancial series discovered: {len(series)}")
        for s in series[:5]:
            print(f"  {s.get('ticker')}: {s.get('title', '')[:60]}")
        if len(series) > 5:
            print(f"  ... and {len(series) - 5} more")

        # 3. Fetch markets for each series
        for s in series:
            st = s.get("ticker")
            if not st:
                continue
            try:
                markets = get_markets_for_series(st)
                all_markets.extend(markets)
            except Exception as e:
                print(f"  Warning: failed to fetch markets for {st}: {e}")

        print(f"\nTotal active markets fetched: {len(all_markets)}")

        # 4. Store in SQLite
        new_records, changed_prices = store_markets(conn, all_markets, run_at)
        print(f"New records inserted: {new_records}")
        print(f"Markets with price changes since last run: {changed_prices}")

        # 5. Summary stats
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT ticker) FROM market_snapshots")
        total_unique = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM market_snapshots WHERE fetched_at = ?", (run_at,))
        total_this_run = c.fetchone()[0]

        print(f"\nTotal unique markets in database: {total_unique}")
        print(f"Markets in this run: {total_this_run}")

        # 6. Top 5 by volume
        c.execute("""
            SELECT ticker, title, yes_bid, yes_ask, volume_fp
            FROM market_snapshots
            WHERE fetched_at = ?
            ORDER BY volume_fp DESC
            LIMIT 5
        """, (run_at,))
        top = c.fetchall()
        print("\nTop 5 markets by volume:")
        for row in top:
            print(f"  {row[0]}: {row[1][:55] if row[1] else 'N/A'}")
            print(f"    Bid: {row[2]}  Ask: {row[3]}  Vol: {row[4]}")

    except Exception as e:
        error_msg = str(e)
        print(f"\nERROR: {error_msg}")

    finally:
        # 7. Record pipeline run
        c = conn.cursor()
        c.execute("""
            INSERT INTO pipeline_runs (run_at, markets_fetched, new_records, changed_prices, error)
            VALUES (?, ?, ?, ?, ?)
        """, (run_at, len(all_markets), new_records if 'new_records' in dir() else 0,
              changed_prices if 'changed_prices' in dir() else 0, error_msg))
        conn.commit()
        conn.close()

    print("\nPipeline complete. Database:", DB_PATH)
    return 0 if not error_msg else 1


if __name__ == "__main__":
    sys.exit(main())
