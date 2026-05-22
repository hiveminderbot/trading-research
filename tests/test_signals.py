"""
Tests for kalshi_signals.py

Validates signal extraction with synthetic data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kalshi_signals import (
    MarketSnapshot, Signal,
    compute_momentum, compute_volatility, compute_volume_zscore,
    compute_mean_reversion, compute_trend_strength,
    compute_signal_score, extract_signals_for_ticker
)


def test_compute_momentum():
    prices = [0.50, 0.52, 0.55, 0.53, 0.60]
    assert compute_momentum(prices, 3) == (0.60 - 0.52) / 0.52
    assert compute_momentum([0.50], 3) is None
    print("PASS: compute_momentum")


def test_compute_volatility():
    prices = [0.50, 0.52, 0.48, 0.51, 0.49]
    vol = compute_volatility(prices, 5)
    assert vol is not None and vol > 0
    assert compute_volatility([0.50], 5) is None
    print("PASS: compute_volatility")


def test_compute_volume_zscore():
    volumes = [100, 110, 90, 105, 200]
    zscore = compute_volume_zscore(volumes, 5)
    assert zscore is not None and zscore > 0  # 200 is above mean of ~101
    print("PASS: compute_volume_zscore")


def test_compute_mean_reversion():
    prices = [0.50, 0.50, 0.50, 0.50, 0.60]
    mr = compute_mean_reversion(prices, 5)
    assert mr is not None and mr > 0  # 0.60 is above mean of 0.50
    print("PASS: compute_mean_reversion")


def test_compute_trend_strength():
    prices_up = [0.50, 0.51, 0.52, 0.53, 0.54]
    assert compute_trend_strength(prices_up) == 4

    prices_down = [0.54, 0.53, 0.52, 0.51, 0.50]
    assert compute_trend_strength(prices_down) == 4

    prices_mixed = [0.50, 0.52, 0.51, 0.53, 0.52]
    assert compute_trend_strength(prices_mixed) == 1  # last move is down
    print("PASS: compute_trend_strength")


def test_compute_signal_score():
    score = compute_signal_score(0.1, 0.05, -0.05, 1.0, 3)
    assert score is not None
    assert -1.0 <= score <= 1.0
    print("PASS: compute_signal_score")


def test_extract_signals_for_ticker():
    snapshots = [
        MarketSnapshot("TEST-1", "Test", 0.50, 0.52, 100, "2026-05-19T10:00:00"),
        MarketSnapshot("TEST-1", "Test", 0.52, 0.54, 150, "2026-05-19T11:00:00"),
        MarketSnapshot("TEST-1", "Test", 0.55, 0.57, 200, "2026-05-19T12:00:00"),
        MarketSnapshot("TEST-1", "Test", 0.53, 0.55, 180, "2026-05-19T13:00:00"),
        MarketSnapshot("TEST-1", "Test", 0.58, 0.60, 250, "2026-05-19T14:00:00"),
    ]
    signals = extract_signals_for_ticker(snapshots)
    assert len(signals) == 5

    # Last signal should have momentum
    last = signals[-1]
    assert last.momentum_3 is not None
    assert last.volatility_5 is not None
    assert last.signal_score is not None
    print("PASS: extract_signals_for_ticker")


def test_signal_score_bounds():
    """Ensure signal_score is always within [-1, 1]."""
    snapshots = [
        MarketSnapshot("TEST-2", "Test", 0.01, 0.02, 1, "2026-05-19T10:00:00"),
        MarketSnapshot("TEST-2", "Test", 0.99, 0.995, 1000000, "2026-05-19T11:00:00"),
    ]
    signals = extract_signals_for_ticker(snapshots)
    for s in signals:
        if s.signal_score is not None:
            assert -1.0 <= s.signal_score <= 1.0, f"Signal score out of bounds: {s.signal_score}"
    print("PASS: signal_score_bounds")


def run_all_tests():
    test_compute_momentum()
    test_compute_volatility()
    test_compute_volume_zscore()
    test_compute_mean_reversion()
    test_compute_trend_strength()
    test_compute_signal_score()
    test_extract_signals_for_ticker()
    test_signal_score_bounds()
    print("\nAll tests passed!")


if __name__ == "__main__":
    run_all_tests()
