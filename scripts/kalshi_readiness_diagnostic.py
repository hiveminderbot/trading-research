#!/usr/bin/env python3
"""Kalshi DB readiness diagnostic for daily accumulation evidence."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def q1(conn: sqlite3.Connection, sql: str, params=()):
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def qall(conn: sqlite3.Connection, sql: str, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="results/kalshi_market_data.db")
    ap.add_argument("--out-prefix", default=None)
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        raise SystemExit(f"DB not found: {db}")

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    latest_run = qall(conn, """
        SELECT run_at, markets_fetched, new_records, changed_prices, error
        FROM pipeline_runs ORDER BY run_at DESC, id DESC LIMIT 1
    """)
    latest = latest_run[0] if latest_run else {}
    latest_run_at = latest.get("run_at")

    date_rows = qall(conn, """
        SELECT date(fetched_at) AS day,
               COUNT(*) AS rows,
               COUNT(DISTINCT ticker) AS tickers,
               SUM(CASE WHEN yes_bid IS NOT NULL AND yes_bid > 0 THEN 1 ELSE 0 END) AS valid_bid_rows,
               SUM(CASE WHEN yes_bid IS NOT NULL AND yes_bid > 0 AND COALESCE(volume_fp,0) > 0 AND COALESCE(open_interest,0) > 0 THEN 1 ELSE 0 END) AS tradeable_rows
        FROM market_snapshots
        GROUP BY date(fetched_at)
        ORDER BY day
    """)

    latest_counts = {}
    if latest_run_at:
        latest_counts = dict(conn.execute("""
            SELECT COUNT(*) AS rows,
                   COUNT(DISTINCT ticker) AS tickers,
                   SUM(CASE WHEN yes_bid IS NOT NULL AND yes_bid > 0 THEN 1 ELSE 0 END) AS valid_bid_rows,
                   SUM(CASE WHEN yes_bid IS NOT NULL AND yes_bid > 0 AND COALESCE(volume_fp,0) > 0 AND COALESCE(open_interest,0) > 0 THEN 1 ELSE 0 END) AS tradeable_rows,
                   SUM(CASE WHEN yes_bid IS NOT NULL AND yes_ask IS NOT NULL AND yes_bid > 0 AND yes_ask > 0 AND yes_ask >= yes_bid THEN 1 ELSE 0 END) AS usable_spread_rows
            FROM market_snapshots WHERE fetched_at = ?
        """, (latest_run_at,)).fetchone())

    ticker_history = dict(conn.execute("""
        SELECT
          SUM(CASE WHEN snapshot_days >= 2 THEN 1 ELSE 0 END) AS tickers_2plus_days,
          SUM(CASE WHEN snapshot_days >= 3 THEN 1 ELSE 0 END) AS tickers_3plus_days,
          SUM(CASE WHEN snapshots >= 2 THEN 1 ELSE 0 END) AS tickers_2plus_snapshots,
          SUM(CASE WHEN snapshots >= 4 THEN 1 ELSE 0 END) AS tickers_4plus_snapshots,
          SUM(CASE WHEN snapshots >= 8 THEN 1 ELSE 0 END) AS tickers_8plus_snapshots
        FROM (
          SELECT ticker, COUNT(*) AS snapshots, COUNT(DISTINCT date(fetched_at)) AS snapshot_days
          FROM market_snapshots
          WHERE yes_bid IS NOT NULL AND yes_bid > 0
          GROUP BY ticker
        )
    """).fetchone())

    cross_day_overlap = qall(conn, """
        SELECT a.day AS day_a, b.day AS day_b, COUNT(*) AS overlapping_tickers
        FROM (
          SELECT DISTINCT date(fetched_at) AS day, ticker
          FROM market_snapshots WHERE yes_bid IS NOT NULL AND yes_bid > 0
        ) a
        JOIN (
          SELECT DISTINCT date(fetched_at) AS day, ticker
          FROM market_snapshots WHERE yes_bid IS NOT NULL AND yes_bid > 0
        ) b ON a.ticker = b.ticker AND a.day < b.day
        GROUP BY a.day, b.day
        ORDER BY a.day, b.day
    """)

    top_repeated = qall(conn, """
        SELECT ticker, COUNT(*) AS snapshots, COUNT(DISTINCT date(fetched_at)) AS days,
               MIN(fetched_at) AS first_seen, MAX(fetched_at) AS last_seen,
               MIN(yes_bid) AS min_bid, MAX(yes_bid) AS max_bid,
               MAX(COALESCE(volume_fp,0)) AS max_volume, MAX(COALESCE(open_interest,0)) AS max_open_interest
        FROM market_snapshots
        WHERE yes_bid IS NOT NULL AND yes_bid > 0
        GROUP BY ticker
        HAVING days >= 2 OR snapshots >= 4
        ORDER BY days DESC, snapshots DESC, max_volume DESC
        LIMIT 25
    """)

    # Backtest summary files produced by kalshi_backtest.py.
    reports_dir = Path("reports")
    backtests = []
    if reports_dir.exists():
        for p in sorted(reports_dir.glob("backtest_*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            backtests.append({
                "file": str(p),
                "strategy_name": data.get("strategy_name"),
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "total_trades": data.get("total_trades"),
                "win_rate": data.get("win_rate"),
                "total_pnl": data.get("total_pnl"),
                "sharpe_ratio": data.get("sharpe_ratio"),
                "max_drawdown": data.get("max_drawdown"),
            })

    positive_backtests = [b for b in backtests if (b.get("total_pnl") or 0) > 0 and (b.get("total_trades") or 0) > 30]
    gate_passing_backtests = [
        b for b in positive_backtests
        if (b.get("sharpe_ratio") or 0) > 0.5 and (b.get("max_drawdown") or 1) < 0.2
    ]
    sufficient_for_capital = bool(
        ticker_history.get("tickers_2plus_days", 0) >= 100
        and latest_counts.get("tradeable_rows", 0) >= 500
        and gate_passing_backtests
    )
    verdict = "READY" if sufficient_for_capital else "NOT READY"
    reasons = []
    if ticker_history.get("tickers_2plus_days", 0) < 100:
        reasons.append(f"Only {ticker_history.get('tickers_2plus_days', 0)} valid-price tickers have 2+ calendar days of history; need >=100.")
    if latest_counts.get("tradeable_rows", 0) < 500:
        reasons.append(f"Latest run has {latest_counts.get('tradeable_rows', 0)} tradeable/liquid rows; target >=500 for broad backtest coverage.")
    if not gate_passing_backtests:
        if positive_backtests:
            names = ", ".join(
                f"{b.get('strategy_name')} (PnL={b.get('total_pnl')}, Sharpe={b.get('sharpe_ratio')}, maxDD={b.get('max_drawdown')})"
                for b in positive_backtests[:5]
            )
            reasons.append(f"Positive PnL exists but fails risk-adjusted gates (Sharpe >0.5 and max drawdown <20% required): {names}.")
        else:
            reasons.append("No strategy with >30 trades has positive PnL in the current backtest outputs.")

    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": str(db),
        "latest_pipeline_run": latest,
        "latest_run_counts": latest_counts,
        "date_coverage": date_rows,
        "history_coverage": ticker_history,
        "cross_day_overlap": cross_day_overlap,
        "top_repeated_tickers": top_repeated,
        "backtest_summary": backtests,
        "capital_readiness_verdict": verdict,
        "not_ready_reasons": reasons,
        "recommendation": "Continue data accumulation; do not deploy capital. Re-run after >=7 calendar days and >=100 tickers with 2+ days of liquid, valid prices, then only advance to paper/live if fee-aware backtests turn positive.",
    }

    out_prefix = args.out_prefix or f"reports/kalshi_readiness_{datetime.now(timezone.utc).date().isoformat()}"
    out_json = Path(out_prefix + ".json")
    out_md = Path(out_prefix + ".md")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(evidence, indent=2, sort_keys=True))

    lines = []
    lines.append(f"# Kalshi Readiness Diagnostic — {datetime.now(timezone.utc).date().isoformat()}")
    lines.append("")
    lines.append(f"**Capital-readiness verdict:** **{verdict}**")
    lines.append("")
    lines.append("## Latest pipeline run")
    lines.append("")
    lines.append(f"- Run: `{latest.get('run_at')}`")
    lines.append(f"- Markets fetched: {latest.get('markets_fetched')}")
    lines.append(f"- New records: {latest.get('new_records')}")
    lines.append(f"- Changed prices: {latest.get('changed_prices')}")
    lines.append(f"- Error: {latest.get('error')}")
    lines.append(f"- Latest valid-bid rows: {latest_counts.get('valid_bid_rows')}")
    lines.append(f"- Latest tradeable/liquid rows (`bid>0`, `volume>0`, `OI>0`): {latest_counts.get('tradeable_rows')}")
    lines.append("")
    lines.append("## Data coverage")
    lines.append("")
    lines.append(f"- Valid-price tickers with 2+ calendar days: {ticker_history.get('tickers_2plus_days')}")
    lines.append(f"- Valid-price tickers with 3+ calendar days: {ticker_history.get('tickers_3plus_days')}")
    lines.append(f"- Valid-price tickers with 2+ snapshots: {ticker_history.get('tickers_2plus_snapshots')}")
    lines.append(f"- Valid-price tickers with 4+ snapshots: {ticker_history.get('tickers_4plus_snapshots')}")
    lines.append("")
    lines.append("### Per-day coverage")
    lines.append("")
    lines.append("| Day | Rows | Tickers | Valid bid rows | Tradeable rows |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in date_rows:
        lines.append(f"| {r['day']} | {r['rows']} | {r['tickers']} | {r['valid_bid_rows']} | {r['tradeable_rows']} |")
    lines.append("")
    lines.append("### Cross-day valid-price ticker overlap")
    lines.append("")
    if cross_day_overlap:
        lines.append("| Day A | Day B | Overlap |")
        lines.append("|---|---|---:|")
        for r in cross_day_overlap:
            lines.append(f"| {r['day_a']} | {r['day_b']} | {r['overlapping_tickers']} |")
    else:
        lines.append("No cross-day overlap found.")
    lines.append("")
    lines.append("## Backtest summary")
    lines.append("")
    lines.append("| Strategy | Period | Trades | Win rate | PnL | Sharpe | Max DD |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for b in backtests:
        lines.append(f"| {b['strategy_name']} | {b['start_date']}→{b['end_date']} | {b['total_trades']} | {b['win_rate']} | {b['total_pnl']} | {b['sharpe_ratio']} | {b['max_drawdown']} |")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    for reason in reasons:
        lines.append(f"- {reason}")
    lines.append("- Do **not** deploy capital or paper-trade this as a candidate strategy yet; current evidence is data accumulation plus backtests that fail the risk-adjusted go/no-go gates.")
    lines.append("- Continue daily snapshots until the 7-day gate, then re-run the same diagnostic and fee-aware backtests.")
    lines.append("")
    lines.append("## Evidence files")
    lines.append("")
    lines.append(f"- JSON: `{out_json}`")
    lines.append(f"- Markdown: `{out_md}`")
    out_md.write_text("\n".join(lines) + "\n")

    print(out_json)
    print(out_md)
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
