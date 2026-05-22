"""
Kalshi Signal Extraction Module

Computes technical indicators from Kalshi prediction-market price history.
Designed for binary event contracts (yes/no markets priced in dollars).

Indicators:
- Momentum: price velocity over N snapshots (percentage)
- Absolute momentum: raw dollar change over N snapshots
- Volatility: rolling standard deviation of mid-price
- Volume anomaly: z-score of volume vs rolling mean
- Mean reversion: deviation from rolling mean
- Trend strength: consecutive same-direction moves
- Spread: bid-ask spread for liquidity filtering
"""

import sqlite3
import statistics
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class MarketSnapshot:
    ticker: str
    title: Optional[str]
    yes_bid: Optional[float]
    yes_ask: Optional[float]
    volume_fp: Optional[float]
    fetched_at: str

    @property
    def mid_price(self) -> Optional[float]:
        if self.yes_bid is not None and self.yes_ask is not None:
            return (self.yes_bid + self.yes_ask) / 2
        return self.yes_bid or self.yes_ask

    @property
    def spread(self) -> Optional[float]:
        if self.yes_bid is not None and self.yes_ask is not None:
            return self.yes_ask - self.yes_bid
        return None


@dataclass
class Signal:
    ticker: str
    fetched_at: str
    mid_price: Optional[float]
    spread: Optional[float]           # bid-ask spread
    momentum_3: Optional[float]       # price change over last 3 snapshots (pct)
    momentum_5: Optional[float]       # price change over last 5 snapshots (pct)
    abs_momentum_1: Optional[float]   # raw dollar change over last 1 snapshot
    abs_momentum_3: Optional[float]   # raw dollar change over last 3 snapshots
    volatility_5: Optional[float]     # rolling std dev of mid-price
    volume_zscore_5: Optional[float]  # volume anomaly
    mean_reversion_5: Optional[float] # deviation from 5-period mean
    trend_strength: Optional[int]     # consecutive same-direction moves
    signal_score: Optional[float]     # composite signal (-1 to +1)


def load_snapshots(db_path: str, ticker: Optional[str] = None) -> List[MarketSnapshot]:
    """Load market snapshots from SQLite DB."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    if ticker:
        c.execute("""
            SELECT ticker, title, yes_bid, yes_ask, volume_fp, fetched_at
            FROM market_snapshots
            WHERE ticker = ? AND yes_bid IS NOT NULL
            ORDER BY fetched_at
        """, (ticker,))
    else:
        c.execute("""
            SELECT ticker, title, yes_bid, yes_ask, volume_fp, fetched_at
            FROM market_snapshots
            WHERE yes_bid IS NOT NULL
            ORDER BY ticker, fetched_at
        """)

    rows = c.fetchall()
    conn.close()

    snapshots = []
    for row in rows:
        snapshots.append(MarketSnapshot(
            ticker=row[0],
            title=row[1],
            yes_bid=row[2],
            yes_ask=row[3],
            volume_fp=row[4],
            fetched_at=row[5]
        ))
    return snapshots


def compute_momentum(prices: List[float], window: int) -> Optional[float]:
    """Price velocity: (current - N periods ago) / N periods ago."""
    if len(prices) < window + 1:
        return None
    prev = prices[-(window + 1)]
    curr = prices[-1]
    if prev == 0:
        return None
    return (curr - prev) / prev


def compute_abs_momentum(prices: List[float], window: int) -> Optional[float]:
    """Raw dollar change: current - N periods ago."""
    if len(prices) < window + 1:
        return None
    prev = prices[-(window + 1)]
    curr = prices[-1]
    return curr - prev


def compute_volatility(prices: List[float], window: int) -> Optional[float]:
    """Rolling standard deviation of prices."""
    if len(prices) < window:
        return None
    recent = prices[-window:]
    if len(recent) < 2:
        return None
    try:
        return statistics.stdev(recent)
    except statistics.StatisticsError:
        return None


def compute_volume_zscore(volumes: List[float], window: int) -> Optional[float]:
    """Z-score of current volume vs rolling mean."""
    if len(volumes) < window:
        return None
    recent = volumes[-window:]
    if len(recent) < 2:
        return None
    try:
        mean = statistics.mean(recent[:-1])
        std = statistics.stdev(recent[:-1])
        if std == 0:
            return 0.0
        return (recent[-1] - mean) / std
    except (statistics.StatisticsError, ZeroDivisionError):
        return None


def compute_mean_reversion(prices: List[float], window: int) -> Optional[float]:
    """Deviation from rolling mean (positive = above mean, negative = below)."""
    if len(prices) < window:
        return None
    recent = prices[-window:]
    try:
        mean = statistics.mean(recent[:-1])
        if mean == 0:
            return None
        return (prices[-1] - mean) / mean
    except statistics.StatisticsError:
        return None


def compute_trend_strength(prices: List[float]) -> Optional[int]:
    """Count consecutive same-direction price moves."""
    if len(prices) < 2:
        return None
    direction = 0
    count = 0
    for i in range(len(prices) - 1, 0, -1):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            curr_dir = 1
        elif diff < 0:
            curr_dir = -1
        else:
            break
        if direction == 0:
            direction = curr_dir
            count = 1
        elif curr_dir == direction:
            count += 1
        else:
            break
    return count if count > 0 else None


def compute_signal_score(
    momentum_3: Optional[float],
    momentum_5: Optional[float],
    mean_reversion: Optional[float],
    volume_zscore: Optional[float],
    trend_strength: Optional[int]
) -> Optional[float]:
    """
    Composite signal score from -1 (strong sell/no) to +1 (strong buy/yes).
    Weights are heuristic and should be calibrated with backtesting.
    """
    scores = []
    weights = []

    if momentum_3 is not None:
        scores.append(momentum_3)
        weights.append(0.20)
    if momentum_5 is not None:
        scores.append(momentum_5)
        weights.append(0.20)
    if mean_reversion is not None:
        # Mean reversion: if price is far above mean, expect downward reversion
        scores.append(-mean_reversion)
        weights.append(0.25)
    if volume_zscore is not None:
        # High volume often confirms moves
        scores.append(min(max(volume_zscore / 3, -1), 1))
        weights.append(0.15)
    if trend_strength is not None:
        # Strong trends persist short-term
        scores.append(min(trend_strength / 5, 1.0))
        weights.append(0.20)

    if not scores:
        return None

    total_weight = sum(weights)
    weighted = sum(s * w for s, w in zip(scores, weights)) / total_weight
    return max(-1.0, min(1.0, weighted))


def extract_signals_for_ticker(snapshots: List[MarketSnapshot]) -> List[Signal]:
    """Extract signals for a single ticker's snapshot history."""
    signals = []
    prices = []
    volumes = []

    for snap in snapshots:
        mp = snap.mid_price
        prices.append(mp if mp is not None else prices[-1] if prices else 0.0)
        volumes.append(snap.volume_fp if snap.volume_fp is not None else 0.0)

        sig = Signal(
            ticker=snap.ticker,
            fetched_at=snap.fetched_at,
            mid_price=mp,
            spread=snap.spread,
            momentum_3=compute_momentum(prices, 3) if len(prices) >= 4 else compute_momentum(prices, 1),
            momentum_5=compute_momentum(prices, 5) if len(prices) >= 6 else None,
            abs_momentum_1=compute_abs_momentum(prices, 1) if len(prices) >= 2 else None,
            abs_momentum_3=compute_abs_momentum(prices, 3) if len(prices) >= 4 else None,
            volatility_5=compute_volatility(prices, 5) if len(prices) >= 5 else compute_volatility(prices, 2),
            volume_zscore_5=compute_volume_zscore(volumes, 5) if len(volumes) >= 5 else compute_volume_zscore(volumes, 2),
            mean_reversion_5=compute_mean_reversion(prices, 5) if len(prices) >= 5 else compute_mean_reversion(prices, 2),
            trend_strength=compute_trend_strength(prices),
            signal_score=None
        )

        sig.signal_score = compute_signal_score(
            sig.momentum_3, sig.momentum_5, sig.mean_reversion_5,
            sig.volume_zscore_5, sig.trend_strength
        )
        signals.append(sig)

    return signals


def extract_all_signals(db_path: str) -> Dict[str, List[Signal]]:
    """Extract signals for all tickers with sufficient history."""
    snapshots = load_snapshots(db_path)

    # Group by ticker
    by_ticker: Dict[str, List[MarketSnapshot]] = {}
    for snap in snapshots:
        by_ticker.setdefault(snap.ticker, []).append(snap)

    signals_by_ticker = {}
    for ticker, snaps in by_ticker.items():
        if len(snaps) >= 2:  # Minimum for basic momentum
            signals_by_ticker[ticker] = extract_signals_for_ticker(snaps)

    return signals_by_ticker


def get_top_signals(signals_by_ticker: Dict[str, List[Signal]], n: int = 10) -> List[Signal]:
    """Get the top N signals by absolute signal score."""
    all_signals = []
    for signals in signals_by_ticker.values():
        if signals:
            all_signals.append(signals[-1])  # Latest signal for each ticker

    all_signals.sort(key=lambda s: abs(s.signal_score or 0), reverse=True)
    return all_signals[:n]


if __name__ == "__main__":
    import os
    db_path = os.environ.get("KALSHI_DB_PATH", "results/kalshi_market_data.db")
    signals = extract_all_signals(db_path)
    print(f"Extracted signals for {len(signals)} tickers")
    top = get_top_signals(signals, 10)
    for s in top:
        mom3_str = f"{s.momentum_3:+.3f}" if s.momentum_3 is not None else "N/A"
        mom5_str = f"{s.momentum_5:+.3f}" if s.momentum_5 is not None else "N/A"
        abs1_str = f"{s.abs_momentum_1:+.3f}" if s.abs_momentum_1 is not None else "N/A"
        vol_str = f"{s.volatility_5:.4f}" if s.volatility_5 is not None else "N/A"
        vol_z_str = f"{s.volume_zscore_5:+.2f}" if s.volume_zscore_5 is not None else "N/A"
        mr_str = f"{s.mean_reversion_5:+.3f}" if s.mean_reversion_5 is not None else "N/A"
        trend_str = str(s.trend_strength) if s.trend_strength is not None else "N/A"
        spread_str = f"{s.spread:.3f}" if s.spread is not None else "N/A"
        print(f"{s.ticker}: score={s.signal_score:+.3f} | "
              f"mom3={mom3_str} | abs1={abs1_str} | spread={spread_str} | "
              f"vol={vol_str} | vol_z={vol_z_str} | "
              f"mr={mr_str} | trend={trend_str}")
