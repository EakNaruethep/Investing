# Investing

These are Eak's stock valuation reports, which use the revised Graham formula and the two-tier buy-signal rules. [CLAUDE.md](CLAUDE.md) describes the method.

## Reports (`output/reports/`)
- `2026-11-16-graham-mag7-valuation.html`: the main report, with buy signals for the Magnificent 7, TSMC and SpaceX. Signal status and checks A–D are at the top.
- `back-test-10-yr.html`: a 10-year backtest (Nov 2016 – Nov 2026) of the two-tier rules.
- `2026-11-18-graham-backtest-10y.html`: the 10-year backtest that compares v1, v2 and the two-tier rules.
- `2026-11-18-graham-backtest-pit.html`: the point-in-time backtest (Nov 2015 – Nov 2026). It drops look-ahead and survivorship bias.

`archive/` holds earlier versions of the reports.

## Scripts (`scripts/backtest/`)
`model2.py` holds the backtest model and its data. `tier.py` runs the two-tier backtest and writes `tier.json`, and `build_tier.py` builds `back-test-10-yr.html` from it. Run them from inside `scripts/backtest/`:

```
python3 tier.py && python3 build_tier.py
```

Much of the 2016–2021 data in that model was entered from memory, not pulled from a data source.

### Point-in-time backtest (no Python needed)
`2026-11-18-graham-backtest-pit.html` tests the two-tier rules for Nov 2015 – Nov 2026 on the 10 largest US companies of early 2015. It uses only SEC 10-K figures that were filed before each decision date, from `data/`. Run these from PowerShell:

```
powershell -File scripts/backtest/pit_backtest.ps1
powershell -File scripts/backtest/build_pit.ps1
```

`pit_backtest.ps1` reads `data/sec`, `data/backtest_inputs.json` and writes `output/backtest_pit.json`. `build_pit.ps1` fills `pit_template.html` with that JSON.

## Dashboards: daily prices and weekly full review (`scripts/dashboard/`)
- **Weekly full review (uses Claude):** refresh the main valuation report: EPS with one-offs removed, g, quality gates, rule C, and news for rule D in `data/d_holds.json`. Then run `build_watchlist.ps1`, which copies each stock's value, buy price and gate results into `data/watchlist.json`.
- **Daily price check (no Claude, no tokens):** `price_watch.ps1` fetches the latest prices from Yahoo and checks them against `data/watchlist.json`, which covers rule A only. It writes `output/dashboard/daily.html` and adds a row per stock to `data/price_history.csv`. It takes about 5 seconds. Pass `-CopyTo <folder>`, for example a OneDrive folder, to read the page on a phone.

```
powershell -File scripts/dashboard/build_watchlist.ps1
powershell -File scripts/dashboard/price_watch.ps1
```

Nothing in this repository is investment advice.
