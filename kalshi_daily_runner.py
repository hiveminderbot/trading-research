"""
Kalshi Daily Runner — Idempotent cron-ready pipeline runner.
Fetches market data, stores in SQLite, generates daily report.
Designed to run via cron without duplicate records.
"""
import urllib.request
import urllib.error
import json
import sqlite3
import ssl
import sys
import os
import time
from datetime import datetime, timezone, timedelta

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
DB_PATH = os.environ.get("KALSHI_DB_PATH", "results/kalshi_market_data.db")
REPORTS_DIR = "reports"
RUN_LOG = "results/daily_run.log"


def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(RUN_LOG, "a") as f:
        f.write(line + "\n")


def fetch_json(path, retries=5):
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=20, context=CTX)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                sleep_sec = 2 ** attempt + 1
                log(f"Rate limited (429), sleeping {sleep_sec}s...")
                time.sleep(sleep_sec)
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
    """Kept for compatibility; bulk fetch no longer uses per-series calls."""
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
    """DEPRECATED: Use fetch_all_markets_bulk() instead to avoid rate limits."""
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


def fetch_all_markets_bulk():
    """
    Fetch all markets via the bulk /markets endpoint with pagination.
    This is ~100x faster than per-series fetching and avoids rate limits.
    Returns a list of all market dicts.
    """
    all_markets = []
    cursor = None
    page = 0
    while page < 50:
        path = "/markets?limit=1000"
        if cursor:
            path += f"&cursor={cursor}"
        data = fetch_json(path)
        batch = data.get("markets", [])
        all_markets.extend(batch)
        cursor = data.get("cursor")
        log(f"Bulk fetch page {page}: {len(batch)} markets, total={len(all_markets)}")
        if not cursor or not batch:
            break
        time.sleep(0.3)
        page += 1
    return all_markets


def filter_financial_markets(all_markets):
    """Filter the full market list for financial/economic keywords."""
    keywords = [
        "FED", "RATE", "INFLATION", "GDP", "NASDAQ", "BTC", "ETH", "CPI",
        "UNEMPLOYMENT", "SPY", "SP500", "DOW", "OIL", "GOLD", "SILVER",
        "TREASURY", "BOND", "YIELD", "FOREX", "USD", "EUR", "GBP", "JPY"
    ]
    financial = []
    for m in all_markets:
        title = (m.get("title") or "").upper()
        ticker = (m.get("ticker") or "").upper()
        series = (m.get("series_ticker") or "").upper()
        for kw in keywords:
            if kw in title or kw in ticker or kw in series:
                financial.append(m)
                break
    return financial


def normalize_market(m):
    """Normalize a market dict from the Kalshi API to DB schema."""
    return {
        "ticker": m.get("ticker"),
        "title": m.get("title"),
        "series_ticker": m.get("series_ticker"),
        "status": m.get("status"),
        "yes_bid": safe_float(m.get("yes_bid_dollars")),
        "yes_ask": safe_float(m.get("yes_ask_dollars")),
        "no_bid": safe_float(m.get("no_bid_dollars")),
        "no_ask": safe_float(m.get("no_ask_dollars")),
        "volume_fp": safe_float(m.get("volume_24h_fp") if m.get("volume_24h_fp") is not None else m.get("volume_fp")),
        "open_interest": safe_float(m.get("open_interest_fp") if m.get("open_interest_fp") is not None else m.get("open_interest")),
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


def generate_daily_report(conn, run_at):
    """Generate a markdown daily report with top movers, new markets, volume anomalies."""
    c = conn.cursor()
    report_path = os.path.join(REPORTS_DIR, f"daily_report_{run_at[:10]}.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Count stats
    c.execute("SELECT COUNT(DISTINCT ticker) FROM market_snapshots")
    total_unique = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_snapshots WHERE fetched_at = ?", (run_at,))
    total_this_run = c.fetchone()[0]

    # Top 10 by volume this run
    c.execute("""
        SELECT ticker, title, yes_bid, yes_ask, volume_fp, volume_24h_fp, open_interest
        FROM market_snapshots
        WHERE fetched_at = ?
        ORDER BY volume_fp DESC
        LIMIT 10
    """, (run_at,))
    top_volume = c.fetchall()

    # Price movers: compare to previous run (same ticker, previous fetched_at)
    c.execute("""
        SELECT a.ticker, a.title, a.yes_bid as current_bid, b.yes_bid as prev_bid,
               a.volume_fp, a.fetched_at, b.fetched_at as prev_fetched_at
        FROM market_snapshots a
        JOIN (
            SELECT ticker, yes_bid, fetched_at,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY fetched_at DESC) as rn
            FROM market_snapshots
        ) b ON a.ticker = b.ticker AND b.rn = 2
        WHERE a.fetched_at = ?
          AND a.yes_bid IS NOT NULL AND b.yes_bid IS NOT NULL
          AND b.yes_bid > 0
        ORDER BY ABS((a.yes_bid - b.yes_bid) / b.yes_bid) DESC
        LIMIT 15
    """, (run_at,))
    movers = c.fetchall()

    # New markets (first appearance)
    c.execute("""
        SELECT ticker, title, yes_bid, yes_ask, volume_fp
        FROM market_snapshots
        WHERE fetched_at = ?
          AND ticker IN (
              SELECT ticker FROM market_snapshots
              GROUP BY ticker HAVING COUNT(*) = 1
          )
        ORDER BY volume_fp DESC
        LIMIT 10
    """, (run_at,))
    new_markets = c.fetchall()

    lines = []
    lines.append(f"# Kalshi Daily Market Report — {run_at[:10]}")
    lines.append("")
    lines.append(f"**Run at:** {run_at}  ")
    lines.append(f"**Total unique markets in DB:** {total_unique}  ")
    lines.append(f"**Markets in this run:** {total_this_run}  ")
    lines.append("")

    lines.append("## Top 10 Markets by Volume")
    lines.append("")
    lines.append("| Ticker | Title | Yes Bid | Yes Ask | Volume | 24h Volume | Open Interest |")
    lines.append("|--------|-------|---------|---------|--------|-----------|---------------|")
    for row in top_volume:
        ticker, title, yes_bid, yes_ask, vol, vol24, oi = row
        lines.append(f"| {ticker} | {title[:50] if title else 'N/A'} | {yes_bid} | {yes_ask} | {vol:,.0f} | {vol24 if vol24 else 'N/A'} | {oi if oi else 'N/A'} |")
    lines.append("")

    lines.append("## Top 15 Price Movers (vs previous snapshot)")
    lines.append("")
    lines.append("| Ticker | Title | Prev Bid | Curr Bid | Change % | Volume |")
    lines.append("|--------|-------|----------|----------|----------|--------|")
    for row in movers:
        ticker, title, curr, prev, vol, _, _ = row
        change_pct = ((curr - prev) / prev) * 100 if prev else 0
        lines.append(f"| {ticker} | {title[:45] if title else 'N/A'} | {prev} | {curr} | {change_pct:+.1f}% | {vol:,.0f} |")
    lines.append("")

    lines.append("## New Markets (first appearance)")
    lines.append("")
    lines.append("| Ticker | Title | Yes Bid | Yes Ask | Volume |")
    lines.append("|--------|-------|---------|---------|--------|")
    for row in new_markets:
        ticker, title, yes_bid, yes_ask, vol = row
        lines.append(f"| {ticker} | {title[:50] if title else 'N/A'} | {yes_bid} | {yes_ask} | {vol:,.0f} |")
    lines.append("")

    lines.append("---")
    lines.append("*Generated by Kalshi Daily Runner*")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    log(f"Daily report written: {report_path}")
    return report_path


def main():
    run_at = datetime.now(timezone.utc).isoformat()
    log("=" * 60)
    log(f"Kalshi Daily Runner — {run_at}")

    conn = init_db()
    error_msg = None
    all_markets = []
    financial = []
    new_records = 0
    changed_prices = 0
    report_path = None

    try:
        status = fetch_json("/exchange/status")
        log(f"Exchange active: {status.get('exchange_active')}")
        if not status.get("exchange_active"):
            raise RuntimeError("Exchange is not active")

        # Use bulk fetch instead of per-series to avoid rate limits
        all_markets = fetch_all_markets_bulk()
        financial = filter_financial_markets(all_markets)
        log(f"Financial markets filtered: {len(financial)} / {len(all_markets)} total")

        new_records, changed_prices = store_markets(conn, financial, run_at)
        log(f"New records: {new_records}, Changed prices: {changed_prices}")

        report_path = generate_daily_report(conn, run_at)

    except Exception as e:
        error_msg = str(e)
        log(f"ERROR: {error_msg}")

    finally:
        c = conn.cursor()
        c.execute("""
            INSERT INTO pipeline_runs (run_at, markets_fetched, new_records, changed_prices, error)
            VALUES (?, ?, ?, ?, ?)
        """, (run_at, len(financial), new_records, changed_prices, error_msg))
        conn.commit()
        conn.close()

    log("Pipeline complete.")
    return 0 if not error_msg else 1


if __name__ == "__main__":
    sys.exit(main())
