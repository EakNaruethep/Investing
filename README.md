# Investing

These are Eak's stock reports. They use the revised Graham formula and the two-tier buy-signal rules described in [CLAUDE.md](CLAUDE.md).

## Reports (`output/reports/`)
There are only two reports:
- `daily-report.html`: runs Tuesday–Saturday at 08:30 Thai time and checks price only (rule A). It compares each stock's latest regular-session price (the last close, or the live price while the market is open) with its buy price. Pre-market and after-hours trades are shown beside it but not used (Eak, 2026-11-26). It is built by `scripts/dashboard/price_watch.py` from `data/watchlist.json`.
- `weekly-report.html`: runs Monday at 08:30 Thai time and does the full review: EPS with one-offs removed, g, value and buy price, the quality gates, rule C and news for rule D. Its layout follows `archive/2026-11-24/2026-11-16-graham-mag7-valuation.html`. Each run copies the previous version to `archive/<date>/`.

All other reports, including the backtests, are kept in `archive/`.

## How the two reports connect
1. The weekly report keeps its per-stock data in a `S={...}` block.
2. `scripts/dashboard/build_watchlist.py` copies that data into `data/watchlist.json`.
3. `data/d_holds.json` lists the stocks blocked by rule D.
4. The daily report reads only `watchlist.json` and live prices, so it is cheap to run.

The cloud routines run on GitHub and follow `scripts/dashboard/daily_report_prompt.md` and `scripts/dashboard/weekly_review_prompt.md`. Eak's PC pulls this repository when it starts up.

```
python3 scripts/dashboard/build_watchlist.py
python3 scripts/dashboard/price_watch.py
```

On Windows without Python, `price_watch.ps1` and `build_watchlist.ps1` do the same job.

## Backtests (`scripts/backtest/`, reports in `archive/`)
- `pit_backtest.ps1` + `build_pit.ps1`: the point-in-time backtest for Nov 2015 – Nov 2026. It uses only 10-K figures that were filed before each decision date. The raw SEC files in `data/sec/` are not committed; download them again when you need them.
- `model2.py`, `tier.py`, `build_tier.py`: the earlier 10-year backtest. Much of its 2016–2021 data was entered from memory.

Nothing in this repository is investment advice.
