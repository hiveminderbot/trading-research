"""
Kalshi Series Fetcher — Fetches all financial markets via series-specific endpoints.
Run this to collect data before updating the daily runner.
"""
import urllib.request
import urllib.error
import json
import ssl
import time
import sys

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
BASE = "https://api.elections.kalshi.com/trade-api/v2"


def fetch(path, retries=5):
    url = f"{BASE}{path}"
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=20, context=CTX)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                sleep_sec = 2 ** attempt + 1
                print(f"Rate limited, sleeping {sleep_sec}s...", file=sys.stderr)
                time.sleep(sleep_sec)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


def main():
    print("Fetching all series...")
    series_data = fetch("/series?limit=1000")
    all_series = series_data.get("series", [])
    print(f"Total series: {len(all_series)}")

    keywords = [
        "FED", "RATE", "INFLATION", "GDP", "NASDAQ", "BTC", "ETH", "CPI",
        "UNEMPLOYMENT", "SPY", "SP500", "DOW", "OIL", "GOLD", "SILVER",
        "TREASURY", "BOND", "YIELD", "FOREX", "USD", "EUR", "GBP", "JPY"
    ]
    financial_series = []
    for s in all_series:
        title = (s.get("title") or "").upper()
        ticker = (s.get("ticker") or "").upper()
        for kw in keywords:
            if kw in title or kw in ticker:
                financial_series.append(s)
                break

    print(f"Financial series: {len(financial_series)}")

    all_markets = []
    series_with_markets = 0
    series_without = 0

    for idx, s in enumerate(financial_series):
        ticker = s.get("ticker", "")
        markets = []
        cursor = None
        page = 0
        while page < 10:
            path = f"/markets?series_ticker={ticker}&limit=1000"
            if cursor:
                path += f"&cursor={cursor}"
            try:
                data = fetch(path)
                batch = data.get("markets", [])
                markets.extend(batch)
                cursor = data.get("cursor")
                if not cursor or not batch:
                    break
                page += 1
                time.sleep(0.2)
            except Exception as e:
                print(f"Error fetching {ticker}: {e}", file=sys.stderr)
                break

        if markets:
            series_with_markets += 1
            all_markets.extend(markets)
        else:
            series_without += 1

        if (idx + 1) % 50 == 0:
            print(f"Progress: {idx+1}/{len(financial_series)} series, {len(all_markets)} markets so far")

    with_prices = [m for m in all_markets if m.get("yes_bid_dollars") is not None or m.get("yes_ask_dollars") is not None]
    print(f"\nDone!")
    print(f"Series with markets: {series_with_markets}")
    print(f"Series without markets: {series_without}")
    print(f"Total markets: {len(all_markets)}")
    print(f"Markets with prices: {len(with_prices)}")

    # Save results
    with open("results/kalshi_financial_markets.json", "w") as f:
        json.dump({
            "series_with_markets": series_with_markets,
            "series_without_markets": series_without,
            "total_markets": len(all_markets),
            "markets_with_prices": len(with_prices),
            "markets": all_markets[:500]  # Save first 500 for inspection
        }, f, indent=2)
    print("Saved results/kalshi_financial_markets.json")


if __name__ == "__main__":
    main()
