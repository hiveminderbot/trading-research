"""
Kalshi Economic Calendar Module

Maps scheduled macroeconomic events to Kalshi prediction market series.
Events: Fed meetings, CPI releases, oil inventory reports, etc.

Usage:
    from economic_calendar import get_upcoming_events, map_events_to_markets
    events = get_upcoming_events(days_ahead=14)
    markets = map_events_to_markets(events, db_path='results/kalshi_market_data.db')
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import sqlite3

# Hard-coded event schedule for 2026
# Sources: FOMC calendar, BLS release calendar, EIA oil report schedule
EVENT_SCHEDULE = [
    # Fed meetings (decision announced at 14:00 ET on final day)
    {'type': 'FOMC', 'date': '2026-06-18', 'series_prefix': 'KXFEDDECISION-26JUN', 'description': 'Fed June 2026 decision'},
    {'type': 'FOMC', 'date': '2026-07-30', 'series_prefix': 'KXFEDDECISION-26JUL', 'description': 'Fed July 2026 decision'},
    {'type': 'FOMC', 'date': '2026-09-17', 'series_prefix': 'KXFEDDECISION-26SEP', 'description': 'Fed Sep 2026 decision'},
    {'type': 'FOMC', 'date': '2026-10-29', 'series_prefix': 'KXFEDDECISION-26OCT', 'description': 'Fed Oct 2026 decision'},
    {'type': 'FOMC', 'date': '2026-12-17', 'series_prefix': 'KXFEDDECISION-26DEC', 'description': 'Fed Dec 2026 decision'},
    {'type': 'FOMC', 'date': '2027-01-27', 'series_prefix': 'KXFEDDECISION-27JAN', 'description': 'Fed Jan 2027 decision'},
    {'type': 'FOMC', 'date': '2027-03-17', 'series_prefix': 'KXFEDDECISION-27MAR', 'description': 'Fed Mar 2027 decision'},
    {'type': 'FOMC', 'date': '2027-04-28', 'series_prefix': 'KXFEDDECISION-27APR', 'description': 'Fed Apr 2027 decision'},
    {'type': 'FOMC', 'date': '2027-06-16', 'series_prefix': 'KXFEDDECISION-27JUN', 'description': 'Fed Jun 2027 decision'},
    {'type': 'FOMC', 'date': '2027-07-28', 'series_prefix': 'KXFEDDECISION-27JUL', 'description': 'Fed Jul 2027 decision'},
    {'type': 'FOMC', 'date': '2027-09-15', 'series_prefix': 'KXFEDDECISION-27SEP', 'description': 'Fed Sep 2027 decision'},
    {'type': 'FOMC', 'date': '2027-10-27', 'series_prefix': 'KXFEDDECISION-27OCT', 'description': 'Fed Oct 2027 decision'},
    {'type': 'FOMC', 'date': '2027-12-15', 'series_prefix': 'KXFEDDECISION-27DEC', 'description': 'Fed Dec 2027 decision'},

    # CPI releases (typically 8:30 ET, 10-15th of following month)
    {'type': 'CPI', 'date': '2026-06-10', 'series_prefix': 'KXCPI-26JUN', 'description': 'CPI June 2026 (MoM)'},
    {'type': 'CPI', 'date': '2026-07-15', 'series_prefix': 'KXCPI-26JUL', 'description': 'CPI July 2026 (MoM)'},
    {'type': 'CPI', 'date': '2026-08-12', 'series_prefix': 'KXCPI-26AUG', 'description': 'CPI Aug 2026 (MoM)'},
    {'type': 'CPI', 'date': '2026-09-16', 'series_prefix': 'KXCPI-26SEP', 'description': 'CPI Sep 2026 (MoM)'},
    {'type': 'CPI', 'date': '2026-10-15', 'series_prefix': 'KXCPI-26OCT', 'description': 'CPI Oct 2026 (MoM)'},
    {'type': 'CPI', 'date': '2026-11-12', 'series_prefix': 'KXCPI-26NOV', 'description': 'CPI Nov 2026 (MoM)'},
    {'type': 'CPI', 'date': '2026-12-10', 'series_prefix': 'KXCPI-26DEC', 'description': 'CPI Dec 2026 (MoM)'},

    # CPI YoY releases (same dates as MoM)
    {'type': 'CPI_YoY', 'date': '2026-06-10', 'series_prefix': 'KXCPIYOY-26JUN', 'description': 'CPI June 2026 (YoY)'},
    {'type': 'CPI_YoY', 'date': '2026-07-15', 'series_prefix': 'KXCPIYOY-26JUL', 'description': 'CPI July 2026 (YoY)'},
    {'type': 'CPI_YoY', 'date': '2026-08-12', 'series_prefix': 'KXCPIYOY-26AUG', 'description': 'CPI Aug 2026 (YoY)'},
    {'type': 'CPI_YoY', 'date': '2026-09-16', 'series_prefix': 'KXCPIYOY-26SEP', 'description': 'CPI Sep 2026 (YoY)'},
    {'type': 'CPI_YoY', 'date': '2026-10-15', 'series_prefix': 'KXCPIYOY-26OCT', 'description': 'CPI Oct 2026 (YoY)'},
    {'type': 'CPI_YoY', 'date': '2026-11-12', 'series_prefix': 'KXCPIYOY-26NOV', 'description': 'CPI Nov 2026 (YoY)'},
    {'type': 'CPI_YoY', 'date': '2026-12-10', 'series_prefix': 'KXCPIYOY-26DEC', 'description': 'CPI Dec 2026 (YoY)'},
]


def get_upcoming_events(days_ahead: int = 14, days_behind: int = 2) -> List[Dict]:
    """Return events within the window."""
    today = date.today()
    upcoming = []
    for event in EVENT_SCHEDULE:
        event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
        days_until = (event_date - today).days
        if -days_behind <= days_until <= days_ahead:
            event_copy = event.copy()
            event_copy['days_until'] = days_until
            upcoming.append(event_copy)
    return upcoming


def map_events_to_markets(events: List[Dict], db_path: str) -> List[Dict]:
    """Map events to available Kalshi markets."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    mapped = []
    for event in events:
        prefix = event['series_prefix']
        c.execute('''
            SELECT DISTINCT ticker, title, yes_bid, yes_ask, volume_fp
            FROM market_snapshots
            WHERE ticker LIKE ? AND yes_bid > 0
            ORDER BY ticker
        ''', (prefix + '%',))
        markets = []
        for row in c.fetchall():
            markets.append({
                'ticker': row[0],
                'title': row[1],
                'yes_bid': row[2],
                'yes_ask': row[3],
                'volume_fp': row[4],
            })

        if markets:
            event_copy = event.copy()
            event_copy['markets'] = markets
            event_copy['market_count'] = len(markets)
            mapped.append(event_copy)

    conn.close()
    return mapped


def get_event_volatility(events: List[Dict], db_path: str) -> List[Dict]:
    """Compute price volatility for event markets over available history."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    results = []
    for event in events:
        prefix = event['series_prefix']
        c.execute('''
            SELECT ticker, MIN(yes_bid) as min_bid, MAX(yes_bid) as max_bid,
                   MAX(yes_bid) - MIN(yes_bid) as swing,
                   COUNT(DISTINCT date(fetched_at)) as days
            FROM market_snapshots
            WHERE ticker LIKE ? AND yes_bid > 0
            GROUP BY ticker
            HAVING days >= 2
            ORDER BY swing DESC
        ''', (prefix + '%',))

        volatile_markets = []
        for row in c.fetchall():
            volatile_markets.append({
                'ticker': row[0],
                'min_bid': row[1],
                'max_bid': row[2],
                'swing': row[3],
                'days': row[4],
            })

        if volatile_markets:
            event_copy = event.copy()
            event_copy['volatile_markets'] = volatile_markets
            event_copy['max_swing'] = max(m['swing'] for m in volatile_markets)
            results.append(event_copy)

    conn.close()
    return results


if __name__ == '__main__':
    events = get_upcoming_events(days_ahead=30)
    print(f'Upcoming events: {len(events)}')
    for e in events:
        print(f"  {e['type']} {e['date']} ({e['days_until']} days): {e['description']}")

    mapped = map_events_to_markets(events, 'results/kalshi_market_data.db')
    print(f'\nEvents with markets: {len(mapped)}')
    for m in mapped:
        print(f"  {m['type']} {m['date']}: {m['market_count']} markets")
