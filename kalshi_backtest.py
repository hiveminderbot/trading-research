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
        # Close if momentum reverses significantly
        if position.side == 'YES' and (mom3 < -0.02 or score < -0.3):
            return 'CLOSE'
        if position.side == 'NO' and (mom3 > 0.02 or score > 0.3):
            return 'CLOSE'
        return 'HOLD'

    # No position - look for entry
    if mom3 > 0.05 and score > 0.2:
        return 'BUY_YES'
    if mom3 < -0.05 and score < -0.2:
        return 'BUY_NO'

    return 'HOLD'


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


def combined_strategy(signals: List[Signal], position: Optional[Position]) -> str:
    """
    Combined strategy: momentum + mean reversion with volume confirmation.
    Requires strong signal_score and volume anomaly for entry.
    """
    if not signals:
        return 'HOLD'

    latest = signals[-1]
    score = latest.signal_score or 0
    vol_z = latest.volume_zscore_5 or 0
    mom3 = latest.momentum_3 or 0
    mr = latest.mean_reversion_5 or 0

    if position:
        # Trailing stop: close if score weakens significantly
        if position.side == 'YES' and (score < -0.1 or mom3 < -0.03):
            return 'CLOSE'
        if position.side == 'NO' and (score > 0.1 or mom3 > 0.03):
            return 'CLOSE'
        return 'HOLD'

    # Entry requires volume confirmation
    if score > 0.4 and vol_z > 0.5 and mom3 > 0.03:
        return 'BUY_YES'
    if score < -0.4 and vol_z > 0.5 and mom3 < -0.03:
        return 'BUY_NO'

    return 'HOLD'


def run_backtest(
    signals_by_ticker: Dict[str, List[Signal]],
    strategy: Callable[[List[Signal], Optional[Position]], str],
    strategy_name: str,
    initial_capital: float = 1000.0,
    position_size: float = 100.0  # Dollar amount per trade
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
        if len(signals) < 3:
            continue

        position: Optional[Position] = None

        for i, sig in enumerate(signals):
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

            elif action == 'BUY_NO' and not position and sig.mid_price is not None:
                position = Position(
                    ticker=ticker,
                    side='NO',
                    entry_price=1.0 - sig.mid_price,  # Price of NO contract
                    entry_time=sig.fetched_at,
                    size=position_size
                )
                trades.append(Trade(
                    ticker=ticker, action='OPEN', side='NO',
                    price=1.0 - sig.mid_price, time=sig.fetched_at
                ))

            elif action == 'CLOSE' and position and sig.mid_price is not None:
                exit_price = sig.mid_price if position.side == 'YES' else 1.0 - sig.mid_price
                pnl = (exit_price - position.entry_price) * position.size
                if position.side == 'NO':
                    pnl = ((1.0 - exit_price) - position.entry_price) * position.size

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
                if position.side == 'NO':
                    pnl = ((1.0 - exit_price) - position.entry_price) * position.size

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
    closed_trades = [t for t in trades if t.action in ('CLOSE', 'EXPIRE')]
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


if __name__ == "__main__":
    import os
    db_path = os.environ.get("KALSHI_DB_PATH", "results/kalshi_market_data.db")

    print("Loading signals...")
    signals = extract_all_signals(db_path)
    print(f"Loaded signals for {len(signals)} tickers")

    if len(signals) < 5:
        print("WARNING: Insufficient data for meaningful backtest.")
        print("Need at least 5 tickers with 3+ snapshots each.")
        print(f"Current: {len(signals)} tickers with sufficient history")
        print("Run the pipeline daily to accumulate data.")
        exit(0)

    strategies = [
        (momentum_strategy, "Momentum Strategy"),
        (mean_reversion_strategy, "Mean Reversion Strategy"),
        (combined_strategy, "Combined Momentum+MeanReversion"),
    ]

    for strat, name in strategies:
        print(f"\nRunning {name}...")
        result = run_backtest(signals, strat, name)
        print(f"  Trades: {result.total_trades}, Win Rate: {result.win_rate:.1%}, PnL: ${result.total_pnl:.2f}")

        report_path = f"reports/backtest_{name.lower().replace(' ', '_')}_{result.end_date}.md"
        generate_backtest_report(result, report_path)
        print(f"  Report: {report_path}")

        json_path = f"reports/backtest_{name.lower().replace(' ', '_')}_{result.end_date}.json"
        with open(json_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"  JSON: {json_path}")
