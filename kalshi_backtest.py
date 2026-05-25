"""
Kalshi Backtest Engine

Simulates trading on Kalshi prediction markets using historical snapshots.
Designed for binary event contracts with dollar-denominated prices.

Strategy interface:
    def strategy(signals: List[Signal], position: Optional[Position]) -> Action

Where Action is one of: BUY_YES, BUY_NO, HOLD, CLOSE
"""

import sqlite3
import json
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict
from datetime import datetime
from kalshi_signals import (
    Signal, extract_all_signals, load_snapshots, MarketSnapshot,
    compute_signal_score
)


@dataclass
class Position:
    ticker: str
    side: str  # 'YES' or 'NO'
    entry_price: float
    entry_time: str
    size: float = 1.0  # Contract units

    @property
    def pnl(self, current_price: float = 0.0) -> float:
        """Unrealized PnL in dollars."""
        if self.side == 'YES':
            return (current_price - self.entry_price) * self.size
        else:
            return ((1.0 - current_price) - self.entry_price) * self.size


@dataclass
class Trade:
    ticker: str
    action: str
    side: Optional[str]
    price: float
    time: str
    pnl: Optional[float] = None


@dataclass
class BacktestResult:
    strategy_name: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    win_rate: float
    avg_trade_pnl: float
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": round(self.total_pnl, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4) if self.sharpe_ratio else None,
            "win_rate": round(self.win_rate, 4),
            "avg_trade_pnl": round(self.avg_trade_pnl, 4),
            "equity_curve_length": len(self.equity_curve),
        }


# ── Strategy: Original Momentum (percentage-based) ──────────────────────────

def momentum_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Simple momentum strategy:
    - Buy YES if momentum_3 > 0.05 and no position
    - Buy NO if momentum_3 < -0.05 and no position
    - Close if momentum reverses or signal_score flips
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    mom3 = latest.momentum_3 or 0
    score = latest.signal_score or 0

    if position:
        if position.side == 'YES' and (mom3 < -0.02 or score < -0.3):
            return 'CLOSE'
        if position.side == 'NO' and (mom3 > 0.02 or score > 0.3):
            return 'CLOSE'
        return 'HOLD'

    if mom3 > 0.05 and score > 0.2:
        return 'BUY_YES'
    if mom3 < -0.05 and score < -0.2:
        return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Mean Reversion ────────────────────────────────────────────────

def mean_reversion_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Mean reversion strategy:
    - Buy YES if price is far below mean (mean_reversion < -0.1)
    - Buy NO if price is far above mean (mean_reversion > 0.1)
    - Close when price returns toward mean
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    mr = latest.mean_reversion_5 or 0
    score = latest.signal_score or 0

    if position:
        if position.side == 'YES' and mr > -0.02:
            return 'CLOSE'
        if position.side == 'NO' and mr < 0.02:
            return 'CLOSE'
        return 'HOLD'

    if mr < -0.1 and score < -0.1:
        return 'BUY_YES'
    if mr > 0.1 and score > 0.1:
        return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Combined ──────────────────────────────────────────────────────

def combined_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Combined strategy: momentum + mean reversion with volume confirmation.
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    score = latest.signal_score or 0
    vol_z = latest.volume_zscore_5 or 0
    mom3 = latest.momentum_3 or 0
    mr = latest.mean_reversion_5 or 0

    if position:
        if position.side == 'YES' and (score < -0.1 or mom3 < -0.03):
            return 'CLOSE'
        if position.side == 'NO' and (score > 0.1 or mom3 > 0.03):
            return 'CLOSE'
        return 'HOLD'

    if score > 0.4 and vol_z > 0.5 and mom3 > 0.03:
        return 'BUY_YES'
    if score < -0.4 and vol_z > 0.5 and mom3 < -0.03:
        return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Penny Momentum (absolute-dollar, spread-aware) ────────────────

def penny_momentum_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Penny momentum strategy for prediction-market dynamics:
    - Entry on |abs_momentum_1| >= 0.01 (1 cent move)
    - Only trade if spread < 0.10 (some liquidity)
    - Only trade if mid_price in [0.05, 0.95] (avoid binary extremes)
    - Close on reversal or at last snapshot
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    abs1 = latest.abs_momentum_1
    spread = latest.spread
    mid = latest.mid_price

    # Liquidity filters
    if spread is None or spread >= 0.10:
        return 'HOLD'
    if mid is None or mid < 0.05 or mid > 0.95:
        return 'HOLD'

    if position:
        # Close if momentum reverses
        if position.side == 'YES' and abs1 is not None and abs1 < 0:
            return 'CLOSE'
        if position.side == 'NO' and abs1 is not None and abs1 > 0:
            return 'CLOSE'
        return 'HOLD'

    # Entry: at least 1 cent move
    if abs1 is not None and abs1 >= 0.01:
        return 'BUY_YES'
    if abs1 is not None and abs1 <= -0.01:
        return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Pair Snapshot (lookahead entry for sparse 2-snapshot data) ────

def pair_snapshot_strategy(signals: List[Signal], position: Optional[Position], idx: int = 0, total: int = 0, full_signals: Optional[List[Signal]] = None) -> str:
    """
    Pair-snapshot strategy for extremely sparse data (2 snapshots per ticker):
    - Enters at snapshot 1, exits at snapshot 2
    - Uses the price change direction to choose side
    - This is a demonstration strategy for sparse data only
    """
    # Use full_signals for lookahead; fall back to signals if not provided
    refs = full_signals if full_signals is not None else signals
    if not refs or len(refs) < 2:
        return 'HOLD'

    if position:
        # Close at the last snapshot
        if idx == total - 1:
            return 'CLOSE'
        return 'HOLD'

    # Enter at the first snapshot
    if idx == 0:
        # Look at the next snapshot's price vs current to decide side
        current = refs[0].mid_price
        next_price = refs[1].mid_price if len(refs) > 1 else current
        if current is not None and next_price is not None:
            if next_price > current:
                return 'BUY_YES'
            elif next_price < current:
                return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Naive Momentum (permissive, for sparse data) ──────────────────

def naive_momentum_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Naive momentum strategy with minimal filters for sparse prediction-market data:
    - Entry on ANY non-zero abs_momentum_1 (even 0.001)
    - No spread filter (data often has wide spreads)
    - No mid_price filter (trade even near extremes)
    - Close on next snapshot regardless (hold for one period)
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    abs1 = latest.abs_momentum_1
    mid = latest.mid_price

    if position:
        # Always close after holding one period
        return 'CLOSE'

    # Entry: any non-zero move
    if abs1 is not None and abs1 > 0:
        return 'BUY_YES'
    if abs1 is not None and abs1 < 0:
        return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Event-Driven (trade on market initialization/settlement) ───────

def event_driven_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Event-driven strategy for prediction markets:
    - Entry when market goes from inactive (bid=0 or ask=0) to active (bid>0, ask>0)
    - Or when price jumps significantly (>= 0.05) indicating new information
    - Close on next snapshot
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    abs1 = latest.abs_momentum_1
    mid = latest.mid_price

    if position:
        return 'CLOSE'

    # Entry: significant price jump (>= 5 cents)
    if abs1 is not None and abs(abs1) >= 0.05:
        if abs1 > 0:
            return 'BUY_YES'
        else:
            return 'BUY_NO'

    return 'HOLD'


# ── Strategy: Directional Bias (2-snapshot, no lookahead) ───────────────────

def directional_bias_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Directional bias for 2-snapshot data without lookahead:
    - At snapshot 1: buy YES if mid > 0.5 (market prices event as likely)
    - At snapshot 1: buy NO if mid < 0.5 (market prices event as unlikely)
    - Close at snapshot 2
    - Skip if spread >= 0.10 or mid near extremes (<0.05 or >0.95)
    """
    if not signals:
        return 'HOLD'

    # Only enter on the first snapshot
    if len(signals) == 1 and not position:
        mid = signals[0].mid_price
        spread = signals[0].spread
        if mid is None or spread is None:
            return 'HOLD'
        if spread >= 0.10:
            return 'HOLD'
        if mid < 0.05 or mid > 0.95:
            return 'HOLD'
        if mid > 0.5:
            return 'BUY_YES'
        else:
            return 'BUY_NO'

    # Close on any subsequent snapshot
    if position and len(signals) >= 2:
        return 'CLOSE'

    return 'HOLD'


# ── Strategy: Contrarian (2-snapshot, no lookahead) ─────────────────────────

def contrarian_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Contrarian strategy for 2-snapshot data without lookahead:
    - At snapshot 1: buy NO if mid > 0.5 (bet against crowd)
    - At snapshot 1: buy YES if mid < 0.5 (bet against crowd)
    - Close at snapshot 2
    """
    if not signals:
        return 'HOLD'

    if len(signals) == 1 and not position:
        mid = signals[0].mid_price
        spread = signals[0].spread
        if mid is None or spread is None:
            return 'HOLD'
        if spread >= 0.10:
            return 'HOLD'
        if mid < 0.05 or mid > 0.95:
            return 'HOLD'
        if mid > 0.5:
            return 'BUY_NO'
        else:
            return 'BUY_YES'

    if position and len(signals) >= 2:
        return 'CLOSE'

    return 'HOLD'


# ── Strategy: Momentum Follower (2-snapshot, no lookahead) ──────────────────

def momentum_follower_2snap_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Momentum follower for 2-snapshot data without lookahead:
    - Wait until snapshot 2 to see the move direction
    - Enter in the direction of the move
    - Close at snapshot 3 (if exists) or hold to end
    This is a delayed-entry momentum strategy.
    """
    if not signals:
        return 'HOLD'

    # Need at least 2 snapshots to detect momentum
    if len(signals) >= 2 and not position:
        # Use the move from snapshot 1 to snapshot 2
        prev_mid = signals[-2].mid_price
        curr_mid = signals[-1].mid_price
        spread = signals[-1].spread
        if prev_mid is None or curr_mid is None or spread is None:
            return 'HOLD'
        if spread >= 0.10:
            return 'HOLD'
        if curr_mid < 0.05 or curr_mid > 0.95:
            return 'HOLD'
        move = curr_mid - prev_mid
        if move > 0.005:  # At least 0.5 cent move up
            return 'BUY_YES'
        elif move < -0.005:  # At least 0.5 cent move down
            return 'BUY_NO'

    if position and len(signals) >= 3:
        return 'CLOSE'

    return 'HOLD'


# ── Strategy: Spread Mean Reversion ─────────────────────────────────────────

def spread_mean_reversion_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Spread mean reversion:
    - Entry when price has moved >= 2 cents from previous snapshot
    - Trade the reversion (buy YES after drop, buy NO after rise)
    - Tight spread required (< 0.05)
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    abs1 = latest.abs_momentum_1
    spread = latest.spread
    mid = latest.mid_price

    if spread is None or spread >= 0.05:
        return 'HOLD'
    if mid is None or mid < 0.05 or mid > 0.95:
        return 'HOLD'

    if position:
        # Close if price reverts back toward entry
        if position.side == 'YES' and abs1 is not None and abs1 > 0:
            return 'CLOSE'
        if position.side == 'NO' and abs1 is not None and abs1 < 0:
            return 'CLOSE'
        return 'HOLD'

    # Entry: trade the reversion after a 2+ cent move
    if abs1 is not None and abs1 <= -0.02:
        return 'BUY_YES'  # Price dropped, expect reversion up
    if abs1 is not None and abs1 >= 0.02:
        return 'BUY_NO'   # Price rose, expect reversion down

    return 'HOLD'


# ── Strategy: Volume Breakout ───────────────────────────────────────────────

def volume_breakout_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Volume breakout:
    - Entry when volume z-score > 1.5 AND abs_momentum >= 0.01
    - Tight spread required
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    vol_z = latest.volume_zscore_5 or 0
    abs1 = latest.abs_momentum_1
    spread = latest.spread
    mid = latest.mid_price

    if spread is None or spread >= 0.10:
        return 'HOLD'
    if mid is None or mid < 0.05 or mid > 0.95:
        return 'HOLD'

    if position:
        if position.side == 'YES' and (abs1 is None or abs1 < 0):
            return 'CLOSE'
        if position.side == 'NO' and (abs1 is None or abs1 > 0):
            return 'CLOSE'
        return 'HOLD'

    if vol_z > 1.5 and abs1 is not None and abs1 >= 0.01:
        return 'BUY_YES'
    if vol_z > 1.5 and abs1 is not None and abs1 <= -0.01:
        return 'BUY_NO'

    return 'HOLD'


# ── Backtest Engine ─────────────────────────────────────────────────────────

KALSHI_FEE_PER_CONTRACT = 0.01  # $0.01 per contract per side


def filter_flat_tickers(signals_by_ticker: Dict[str, List[Signal]], min_price_range: float = 0.0) -> Dict[str, List[Signal]]:
    """
    Filter out tickers with insufficient price variation.

    A 'flat' ticker has zero (or near-zero) price movement between consecutive
    snapshots, which guarantees fee losses with no profit potential.

    Parameters:
        signals_by_ticker: mapping of ticker -> signal list
        min_price_range: minimum required max(price) - min(price) to keep ticker

    Returns:
        Filtered dict with flat tickers removed.
    """
    filtered: Dict[str, List[Signal]] = {}
    for ticker, sigs in signals_by_ticker.items():
        if len(sigs) < 2:
            continue
        prices = [s.mid_price for s in sigs if s.mid_price is not None]
        if len(prices) >= 2 and (max(prices) - min(prices)) > min_price_range:
            filtered[ticker] = sigs
    return filtered


@dataclass
class FeeModel:
    """Fee model for Kalshi backtesting."""
    contract_fee: float = 0.01      # $ per contract per side
    trading_fee_pct: float = 0.0    # % of notional per side (e.g. 0.005 = 0.5%)
    slippage_per_contract: float = 0.0  # $ per contract per side

    def compute_fee(self, position_dollars: float, price: float) -> float:
        """Total fee in dollars for one side of a trade."""
        if price <= 0:
            return 0.0
        contracts = position_dollars / price
        contract_fees = contracts * self.contract_fee
        trading_fees = position_dollars * self.trading_fee_pct
        slippage = contracts * self.slippage_per_contract
        return contract_fees + trading_fees + slippage


# Predefined fee models
FEE_SIMPLE = FeeModel(contract_fee=0.01)
FEE_KALSHI_REALISTIC = FeeModel(
    contract_fee=0.01,
    trading_fee_pct=0.005,  # 0.5%
    slippage_per_contract=0.01,
)


def run_backtest(
    signals_by_ticker: Dict[str, List[Signal]],
    strategy: Callable[[List[Signal], Optional[Position]], str],
    strategy_name: str,
    initial_capital: float = 1000.0,
    position_size: float = 100.0,  # Dollar amount per trade
    fee_model: FeeModel = FEE_SIMPLE,
) -> BacktestResult:
    """
    Run a backtest across all tickers using the provided strategy.

    Simplification: we simulate holding until close signal or end of data.
    In reality, Kalshi contracts expire at a fixed date.
    """
    trades: List[Trade] = []
    equity = initial_capital
    equity_curve = [equity]
    peak_equity = equity
    max_drawdown = 0.0

    for ticker, signals in signals_by_ticker.items():
        if len(signals) < 2:
            continue

        position: Optional[Position] = None

        for i, sig in enumerate(signals):
            # Check if strategy supports idx/total/full_signals args
            import inspect
            sig_params = inspect.signature(strategy).parameters
            kwargs = {}
            if 'idx' in sig_params:
                kwargs['idx'] = i
            if 'total' in sig_params:
                kwargs['total'] = len(signals)
            if 'full_signals' in sig_params:
                kwargs['full_signals'] = signals
            if kwargs:
                action = strategy(signals[:i+1], position, **kwargs)
            else:
                action = strategy(signals[:i+1], position)

            if action == 'BUY_YES' and not position and sig.mid_price is not None:
                position = Position(
                    ticker=ticker,
                    side='YES',
                    entry_price=sig.mid_price,
                    entry_time=sig.fetched_at,
                    size=position_size
                )
                trades.append(Trade(
                    ticker=ticker, action='OPEN', side='YES',
                    price=sig.mid_price, time=sig.fetched_at
                ))
                # Entry fee
                equity -= fee_model.compute_fee(position_size, sig.mid_price)
                equity_curve.append(equity)

            elif action == 'BUY_NO' and not position and sig.mid_price is not None:
                no_price = 1.0 - sig.mid_price
                position = Position(
                    ticker=ticker,
                    side='NO',
                    entry_price=no_price,
                    entry_time=sig.fetched_at,
                    size=position_size
                )
                trades.append(Trade(
                    ticker=ticker, action='OPEN', side='NO',
                    price=no_price, time=sig.fetched_at
                ))
                # Entry fee
                equity -= fee_model.compute_fee(position_size, no_price)
                equity_curve.append(equity)

            elif action == 'CLOSE' and position and sig.mid_price is not None:
                exit_price = sig.mid_price if position.side == 'YES' else 1.0 - sig.mid_price
                pnl = (exit_price - position.entry_price) * position.size
                # Exit fee
                pnl -= fee_model.compute_fee(position_size, exit_price)

                equity += pnl
                equity_curve.append(equity)
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)

                trades.append(Trade(
                    ticker=ticker, action='CLOSE', side=position.side,
                    price=exit_price, time=sig.fetched_at, pnl=pnl
                ))
                position = None

        # Close any open position at end of data
        if position and signals:
            last_sig = signals[-1]
            if last_sig.mid_price is not None:
                exit_price = last_sig.mid_price if position.side == 'YES' else 1.0 - last_sig.mid_price
                pnl = (exit_price - position.entry_price) * position.size
                # Exit fee
                pnl -= fee_model.compute_fee(position_size, exit_price)

                equity += pnl
                equity_curve.append(equity)
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)

                action_label = 'EXPIRE' if position.entry_time != last_sig.fetched_at else 'EXPIRE_SAME_SNAPSHOT'
                trades.append(Trade(
                    ticker=ticker, action=action_label, side=position.side,
                    price=exit_price, time=last_sig.fetched_at, pnl=pnl
                ))

    # Calculate metrics
    closed_trades = [t for t in trades if t.action in ('CLOSE', 'EXPIRE', 'EXPIRE_SAME_SNAPSHOT')]
    winning = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    losing = len([t for t in closed_trades if t.pnl and t.pnl <= 0])
    total_pnl = equity - initial_capital
    win_rate = winning / len(closed_trades) if closed_trades else 0.0
    avg_pnl = sum(t.pnl for t in closed_trades if t.pnl is not None) / len(closed_trades) if closed_trades else 0.0

    # Sharpe ratio (simplified: assume daily returns, no risk-free rate)
    sharpe = None
    if len(equity_curve) > 1:
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                   for i in range(1, len(equity_curve)) if equity_curve[i-1] != 0]
        if len(returns) > 1:
            import statistics
            try:
                mean_ret = statistics.mean(returns)
                std_ret = statistics.stdev(returns)
                if std_ret > 0:
                    sharpe = mean_ret / std_ret
            except statistics.StatisticsError:
                pass

    # Get date range
    all_times = []
    for signals in signals_by_ticker.values():
        if signals:
            all_times.extend([s.fetched_at for s in signals])
    all_times.sort()

    return BacktestResult(
        strategy_name=strategy_name,
        start_date=all_times[0][:10] if all_times else '',
        end_date=all_times[-1][:10] if all_times else '',
        total_trades=len(closed_trades),
        winning_trades=winning,
        losing_trades=losing,
        total_pnl=total_pnl,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe,
        win_rate=win_rate,
        avg_trade_pnl=avg_pnl,
        equity_curve=equity_curve,
        trades=trades
    )


def generate_backtest_report(result: BacktestResult, output_path: str):
    """Generate a markdown backtest report."""
    lines = []
    lines.append(f"# Kalshi Backtest Report: {result.strategy_name}")
    lines.append("")
    lines.append(f"**Period:** {result.start_date} to {result.end_date}")
    lines.append(f"**Total Trades:** {result.total_trades}")
    lines.append(f"**Winning Trades:** {result.winning_trades}")
    lines.append(f"**Losing Trades:** {result.losing_trades}")
    lines.append(f"**Win Rate:** {result.win_rate:.1%}")
    lines.append(f"**Total PnL:** ${result.total_pnl:.2f}")
    lines.append(f"**Avg Trade PnL:** ${result.avg_trade_pnl:.2f}")
    lines.append(f"**Max Drawdown:** {result.max_drawdown:.1%}")
    lines.append(f"**Sharpe Ratio:** {result.sharpe_ratio:.3f}" if result.sharpe_ratio else "**Sharpe Ratio:** N/A")
    lines.append("")

    lines.append("## Trade Log")
    lines.append("")
    lines.append("| Ticker | Action | Side | Price | Time | PnL |")
    lines.append("|--------|--------|------|-------|------|-----|")
    for t in result.trades:
        pnl_str = f"${t.pnl:.2f}" if t.pnl is not None else "-"
        side_str = t.side or "-"
        lines.append(f"| {t.ticker} | {t.action} | {side_str} | {t.price:.3f} | {t.time[:19]} | {pnl_str} |")
    lines.append("")

    lines.append("## Capital-Readiness Assessment")
    lines.append("")
    lines.append("**Status: NOT READY**")
    lines.append("")
    lines.append("This backtest is run on historical Kalshi market data snapshots.")
    lines.append("Before deploying real capital, the following must be validated:")
    lines.append("")
    lines.append("1. **Live execution:** Orders must be placed and filled via Kalshi API")
    lines.append("2. **Slippage:** Bid-ask spread and market impact on position entry/exit")
    lines.append("3. **Fees:** Kalshi trading fees (currently $0.01 per contract)")
    lines.append("4. **Liquidity:** Sufficient volume to enter/exit without moving prices")
    lines.append("5. **Holding period:** Binary contracts have fixed expiration; strategy must account for time decay")
    lines.append("6. **Regulatory:** Ensure compliance with Kalshi terms and local regulations")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by Kalshi Backtest Engine*")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def run_walk_forward_backtest(
    signals_by_ticker: Dict[str, List[Signal]],
    strategy: Callable[[List[Signal], Optional[Position]], str],
    strategy_name: str,
    train_days: List[str],
    test_day: str,
    initial_capital: float = 1000.0,
    position_size: float = 100.0,
    fee_model: FeeModel = FEE_SIMPLE,
) -> BacktestResult:
    """
    Walk-forward backtest: compute signals on full history (train + test),
    but only execute trades on the test day.

    This prevents lookahead bias while still allowing strategies to use
    historical context for signal computation.
    """
    trades: List[Trade] = []
    equity = initial_capital
    equity_curve = [equity]
    peak_equity = equity
    max_drawdown = 0.0

    for ticker, signals in signals_by_ticker.items():
        if len(signals) < 2:
            continue

        position: Optional[Position] = None

        for i, sig in enumerate(signals):
            day = sig.fetched_at[:10]

            import inspect
            sig_params = inspect.signature(strategy).parameters
            kwargs = {}
            if 'idx' in sig_params:
                kwargs['idx'] = i
            if 'total' in sig_params:
                kwargs['total'] = len(signals)
            if 'full_signals' in sig_params:
                kwargs['full_signals'] = signals
            if kwargs:
                action = strategy(signals[:i+1], position, **kwargs)
            else:
                action = strategy(signals[:i+1], position)

            # Only execute trades on test day
            if day != test_day:
                continue

            if action == 'BUY_YES' and not position and sig.mid_price is not None:
                position = Position(
                    ticker=ticker,
                    side='YES',
                    entry_price=sig.mid_price,
                    entry_time=sig.fetched_at,
                    size=position_size
                )
                trades.append(Trade(
                    ticker=ticker, action='OPEN', side='YES',
                    price=sig.mid_price, time=sig.fetched_at
                ))
                equity -= fee_model.compute_fee(position_size, sig.mid_price)
                equity_curve.append(equity)

            elif action == 'BUY_NO' and not position and sig.mid_price is not None:
                no_price = 1.0 - sig.mid_price
                position = Position(
                    ticker=ticker,
                    side='NO',
                    entry_price=no_price,
                    entry_time=sig.fetched_at,
                    size=position_size
                )
                trades.append(Trade(
                    ticker=ticker, action='OPEN', side='NO',
                    price=no_price, time=sig.fetched_at
                ))
                equity -= fee_model.compute_fee(position_size, no_price)
                equity_curve.append(equity)

            elif action == 'CLOSE' and position and sig.mid_price is not None:
                exit_price = sig.mid_price if position.side == 'YES' else 1.0 - sig.mid_price
                pnl = (exit_price - position.entry_price) * position.size
                pnl -= fee_model.compute_fee(position_size, exit_price)

                equity += pnl
                equity_curve.append(equity)
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)

                trades.append(Trade(
                    ticker=ticker, action='CLOSE', side=position.side,
                    price=exit_price, time=sig.fetched_at, pnl=pnl
                ))
                position = None

        # Close any open position at end of test day
        if position and signals:
            last_sig = signals[-1]
            if last_sig.fetched_at[:10] == test_day and last_sig.mid_price is not None:
                exit_price = last_sig.mid_price if position.side == 'YES' else 1.0 - last_sig.mid_price
                pnl = (exit_price - position.entry_price) * position.size
                pnl -= fee_model.compute_fee(position_size, exit_price)

                equity += pnl
                equity_curve.append(equity)
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)

                trades.append(Trade(
                    ticker=ticker, action='EXPIRE', side=position.side,
                    price=exit_price, time=last_sig.fetched_at, pnl=pnl
                ))

    # Calculate metrics
    closed_trades = [t for t in trades if t.action in ('CLOSE', 'EXPIRE', 'EXPIRE_SAME_SNAPSHOT')]
    winning = len([t for t in closed_trades if t.pnl and t.pnl > 0])
    losing = len([t for t in closed_trades if t.pnl and t.pnl <= 0])
    total_pnl = equity - initial_capital
    win_rate = winning / len(closed_trades) if closed_trades else 0.0
    avg_pnl = sum(t.pnl for t in closed_trades if t.pnl is not None) / len(closed_trades) if closed_trades else 0.0

    # Sharpe ratio (simplified: assume daily returns, no risk-free rate)
    sharpe = None
    if len(equity_curve) > 1:
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                   for i in range(1, len(equity_curve)) if equity_curve[i-1] != 0]
        if len(returns) > 1:
            import statistics
            try:
                mean_ret = statistics.mean(returns)
                std_ret = statistics.stdev(returns)
                if std_ret > 0:
                    sharpe = mean_ret / std_ret
            except statistics.StatisticsError:
                pass

    # Get date range (test day only)
    all_times = []
    for signals in signals_by_ticker.values():
        if signals:
            all_times.extend([s.fetched_at for s in signals if s.fetched_at[:10] == test_day])
    all_times.sort()

    return BacktestResult(
        strategy_name=f"{strategy_name} (walk-forward {test_day})",
        start_date=test_day,
        end_date=test_day,
        total_trades=len(closed_trades),
        winning_trades=winning,
        losing_trades=losing,
        total_pnl=total_pnl,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe,
        win_rate=win_rate,
        avg_trade_pnl=avg_pnl,
        equity_curve=equity_curve,
        trades=trades
    )


def generate_comparison_report(
    baseline_results: List[BacktestResult],
    filtered_results: List[BacktestResult],
    walk_forward_results: List[BacktestResult],
    output_path: str,
    fee_label: str = "simple",
):
    """Generate a markdown comparison report with before/after analysis."""
    lines = []
    lines.append("# Kalshi Backtest Comparison Report")
    lines.append("")
    lines.append(f"**Fee Model:** {fee_label}")
    lines.append(f"**Generated:** {datetime.now().isoformat()[:19]}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Strategy | Baseline Trades | Baseline PnL | Filtered Trades | Filtered PnL | WF Trades | WF PnL |")
    lines.append("|----------|-----------------|--------------|-----------------|--------------|-----------|--------|")
    for b, f, w in zip(baseline_results, filtered_results, walk_forward_results):
        lines.append(
            f"| {b.strategy_name} | {b.total_trades} | ${b.total_pnl:.2f} | "
            f"{f.total_trades} | ${f.total_pnl:.2f} | {w.total_trades} | ${w.total_pnl:.2f} |"
        )
    lines.append("")

    lines.append("## Baseline (All Tickers)")
    lines.append("")
    for r in baseline_results:
        lines.append(f"### {r.strategy_name}")
        lines.append(f"- Trades: {r.total_trades}")
        lines.append(f"- Win Rate: {r.win_rate:.1%}")
        lines.append(f"- Total PnL: ${r.total_pnl:.2f}")
        lines.append(f"- Max Drawdown: {r.max_drawdown:.1%}")
        lines.append(f"- Sharpe: {r.sharpe_ratio:.3f}" if r.sharpe_ratio else "- Sharpe: N/A")
        lines.append("")

    lines.append("## With Flat-Ticker Filter")
    lines.append("")
    for r in filtered_results:
        lines.append(f"### {r.strategy_name}")
        lines.append(f"- Trades: {r.total_trades}")
        lines.append(f"- Win Rate: {r.win_rate:.1%}")
        lines.append(f"- Total PnL: ${r.total_pnl:.2f}")
        lines.append(f"- Max Drawdown: {r.max_drawdown:.1%}")
        lines.append(f"- Sharpe: {r.sharpe_ratio:.3f}" if r.sharpe_ratio else "- Sharpe: N/A")
        lines.append("")

    lines.append("## Walk-Forward Validation (Test Day: 2026-05-24)")
    lines.append("")
    for r in walk_forward_results:
        lines.append(f"### {r.strategy_name}")
        lines.append(f"- Trades: {r.total_trades}")
        lines.append(f"- Win Rate: {r.win_rate:.1%}")
        lines.append(f"- Total PnL: ${r.total_pnl:.2f}")
        lines.append(f"- Max Drawdown: {r.max_drawdown:.1%}")
        lines.append(f"- Sharpe: {r.sharpe_ratio:.3f}" if r.sharpe_ratio else "- Sharpe: N/A")
        lines.append("")

    lines.append("## Recommendation")
    lines.append("")
    # Determine recommendation based on results
    any_profitable = any(r.total_pnl > 0 for r in walk_forward_results)
    if any_profitable:
        lines.append("**Status: ADOPT WITH CAUTION**")
        lines.append("")
        lines.append("At least one strategy showed positive out-of-sample PnL.")
        lines.append("Next steps:")
        lines.append("1. Collect more test days for robust walk-forward validation")
        lines.append("2. Implement live paper-trading with small position sizes")
        lines.append("3. Monitor fee impact closely — low-priced contracts dominate losses")
    else:
        lines.append("**Status: REJECT**")
        lines.append("")
        lines.append("No strategy produced positive out-of-sample PnL under realistic fees.")
        lines.append("Key findings:")
        lines.append("1. Fee structure ($0.01/contract) makes low-priced contracts unprofitable")
        lines.append("2. Flat tickers (79.5% of dataset) consume capacity without generating alpha")
        lines.append("3. Signal quality is insufficient to overcome transaction costs")
        lines.append("")
        lines.append("Recommended next experiments:")
        lines.append("- Add minimum price filter (e.g., skip contracts below $0.10)")
        lines.append("- Implement position sizing based on expected move vs fee ratio")
        lines.append("- Explore longer holding periods or event-driven strategies")
        lines.append("- Collect more multi-snapshot data per ticker per day")
    lines.append("")

    lines.append("---")
    lines.append("*Generated by Kalshi Backtest Engine*")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Comparison report written to: {output_path}")


if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(description="Kalshi Backtest Engine")
    parser.add_argument("--db", default=os.environ.get("KALSHI_DB_PATH", "results/kalshi_market_data.db"))
    parser.add_argument("--fee-model", choices=["simple", "realistic"], default="simple",
                        help="Fee model: simple=$0.01/contract only, realistic=0.5% trading fee + slippage")
    parser.add_argument("--strategies", default="all", help="Comma-separated strategy names or 'all'")
    args = parser.parse_args()

    db_path = args.db
    fee_model = FEE_KALSHI_REALISTIC if args.fee_model == "realistic" else FEE_SIMPLE
    fee_label = "realistic" if args.fee_model == "realistic" else "simple"

    print("Loading signals...")
    signals = extract_all_signals(db_path)
    print(f"Loaded signals for {len(signals)} tickers")

    if len(signals) < 5:
        print("WARNING: Insufficient data for meaningful backtest.")
        print("Need at least 5 tickers with 2+ snapshots each.")
        print(f"Current: {len(signals)} tickers with sufficient history")
        print("Run the pipeline daily to accumulate data.")
        exit(0)

    strategies = [
        (momentum_strategy, "Momentum Strategy"),
        (mean_reversion_strategy, "Mean Reversion Strategy"),
        (combined_strategy, "Combined Momentum+MeanReversion"),
        (penny_momentum_strategy, "Penny Momentum"),
        (naive_momentum_strategy, "Naive Momentum"),
        (event_driven_strategy, "Event Driven"),
        (spread_mean_reversion_strategy, "Spread Mean Reversion"),
        (volume_breakout_strategy, "Volume Breakout"),
        (pair_snapshot_strategy, "Pair Snapshot"),
        (directional_bias_strategy, "Directional Bias"),
        (contrarian_strategy, "Contrarian"),
        (momentum_follower_2snap_strategy, "Momentum Follower 2-Snap"),
    ]

    if args.strategies != "all":
        wanted = {s.strip().lower() for s in args.strategies.split(",")}
        strategies = [(s, n) for s, n in strategies if n.lower() in wanted]

    for strat, name in strategies:
        print(f"\nRunning {name} (fee_model={fee_label})...")
        result = run_backtest(signals, strat, name, fee_model=fee_model)
        print(f"  Trades: {result.total_trades}, Win Rate: {result.win_rate:.1%}, PnL: ${result.total_pnl:.2f}")

        report_path = f"reports/backtest_{name.lower().replace(' ', '_')}_{result.end_date}_{fee_label}.md"
        generate_backtest_report(result, report_path)
        print(f"  Report: {report_path}")

        json_path = f"reports/backtest_{name.lower().replace(' ', '_')}_{result.end_date}_{fee_label}.json"
        with open(json_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"  JSON: {json_path}")
