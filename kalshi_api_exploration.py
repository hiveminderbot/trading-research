"""
Kalshi API Exploration Script
Fetches public market data without authentication.
Demonstrates API connectivity and market discovery.
"""
import urllib.request
import json
import ssl
import sys

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


def fetch_json(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15, context=CTX)
    return json.loads(resp.read().decode())


def main():
    results = {}

    # 1. Exchange status
    try:
        status = fetch_json("/exchange/status")
        results["exchange_status"] = status
        print(f"Exchange active: {status.get('exchange_active')}")
        print(f"Trading active: {status.get('trading_active')}")
    except Exception as e:
        results["exchange_status_error"] = str(e)
        print(f"Exchange status error: {e}")

    # 2. Find financial series
    try:
        series_data = fetch_json("/series?limit=200")
        series = series_data.get("series", [])
        keywords = ["FED", "RATE", "INFLATION", "GDP", "NASDAQ", "BTC", "ETH", "CPI", "UNEMPLOYMENT"]
        financial = []
        for s in series:
            title = (s.get("title") or "").upper()
            ticker = (s.get("ticker") or "").upper()
            for kw in keywords:
                if kw in title or kw in ticker:
                    financial.append(s)
                    break
        results["financial_series_count"] = len(financial)
        results["financial_series_sample"] = [
            {"ticker": s.get("ticker"), "title": s.get("title")}
            for s in financial[:10]
        ]
        print(f"\nFinancial series found: {len(financial)}")
    except Exception as e:
        results["series_error"] = str(e)
        print(f"Series error: {e}")

    # 3. Get active rate-cut markets
    try:
        markets_data = fetch_json("/markets?series_ticker=KXRATECUTCOUNT&limit=50")
        markets = markets_data.get("markets", [])
        active = [m for m in markets if m.get("status") == "active"]
        active.sort(key=lambda x: float(x.get("volume_fp", 0) or 0), reverse=True)
        results["rate_cut_markets_count"] = len(active)
        results["top_rate_cut_markets"] = []
        print(f"\nActive rate-cut markets: {len(active)}")
        for m in active[:5]:
            entry = {
                "ticker": m.get("ticker"),
                "title": m.get("title"),
                "yes_bid": m.get("yes_bid_dollars"),
                "yes_ask": m.get("yes_ask_dollars"),
                "volume": m.get("volume_fp"),
                "status": m.get("status"),
            }
            results["top_rate_cut_markets"].append(entry)
            print(f"  {m.get('ticker')}: {m.get('title')[:60]}")
            print(f"    Yes bid: {m.get('yes_bid_dollars')}  Yes ask: {m.get('yes_ask_dollars')}  Vol: {m.get('volume_fp')}")
    except Exception as e:
        results["markets_error"] = str(e)
        print(f"Markets error: {e}")

    # 4. Get orderbook for most liquid market
    try:
        if active:
            top_ticker = active[0]["ticker"]
            ob = fetch_json(f"/markets/{top_ticker}/orderbook")
            yes_orders = ob.get("orderbook_fp", {}).get("yes_dollars", [])
            no_orders = ob.get("orderbook_fp", {}).get("no_dollars", [])
            results["orderbook"] = {
                "ticker": top_ticker,
                "yes_orders_count": len(yes_orders),
                "no_orders_count": len(no_orders),
                "top_yes_bid": yes_orders[0] if yes_orders else None,
                "top_no_bid": no_orders[0] if no_orders else None,
            }
            print(f"\nOrderbook for {top_ticker}:")
            print(f"  Yes orders: {len(yes_orders)}")
            print(f"  No orders: {len(no_orders)}")
            if yes_orders:
                print(f"  Top yes bid: price={yes_orders[0][0]} size={yes_orders[0][1]}")
    except Exception as e:
        results["orderbook_error"] = str(e)
        print(f"Orderbook error: {e}")

    # 5. Auth-required endpoint test (expected 401)
    try:
        fetch_json("/portfolio/balance")
        results["auth_test"] = "unexpected_success"
    except urllib.error.HTTPError as e:
        results["auth_test"] = f"expected_401_{e.code}"
        print(f"\nAuth test (expected 401): {e.code}")

    # Save results
    with open("results/kalshi_api_exploration_2026-05-19.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to results/kalshi_api_exploration_2026-05-19.json")


if __name__ == "__main__":
    main()
