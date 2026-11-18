# Investing

These are Eak's stock valuation reports, which use the revised Graham formula and the two-tier buy-signal rules. [CLAUDE.md](CLAUDE.md) describes the method.

## Reports (`output/reports/`)
- `2026-11-16-graham-mag7-valuation.html`: the main report, with buy signals for the Magnificent 7, TSMC and SpaceX. Signal status and checks A–D are at the top.
- `back-test-10-yr.html`: a 10-year backtest (Nov 2016 – Nov 2026) of the two-tier rules.
- `2026-11-18-graham-backtest-10y.html`: the 10-year backtest that compares v1, v2 and the two-tier rules.

`archive/` holds earlier versions of the reports.

## Scripts (`scripts/backtest/`)
`model2.py` holds the backtest model and its data. `tier.py` runs the two-tier backtest and writes `tier.json`, and `build_tier.py` builds `back-test-10-yr.html` from it. Run them from inside `scripts/backtest/`:

```
python3 tier.py && python3 build_tier.py
```

Much of the 2016–2021 data was entered from memory, not pulled from a data source. Nothing in this repository is investment advice.
