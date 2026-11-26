# Weekly report (every Monday 08:30 Thai time)

Weekly full review of Eak's watchlist with the two-tier Graham buy rules. Work in the root of this repository and follow CLAUDE.md exactly (method, weights, rules A–D). Write the report in Thai. This analyses a method; it is not investment advice, and never execute trades.

Stocks: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, TSM (ADR, USD) and SpaceX (SPCX).

**Every number must be the latest available when the run starts, and every outside number except news comes from the scripts, not from web pages you read yourself** (this keeps the run cheap). Prices are decided on the latest regular-session price (the last close, or the live price while the market is open); pre-market and after-hours trades are shown beside it only. `refresh_weekly.py` does this through `price_watch.quote()`. Fundamentals and Aaa come from `fetch_fundamentals.py`.

Steps
0. Run `python3 scripts/dashboard/fetch_fundamentals.py`. It fetches Moody's Aaa (FRED), the latest quarterly statements (Yahoo, appended to `scripts/backtest/q_<T>.csv`), annual EPS history (SEC) and TWD/USD, and prints one table: TTM GAAP EPS, EPS CAGR 3y/5y, loss in 3y, operating margin, ROE, q, cf, bs, gate, rule C and the run of negative-FCF quarters. Read that table and `data/fundamentals.json`; do not look these numbers up on the web. If a fetch fails, the script says so: report it and carry on with the saved data.
1. Copy the current `output/reports/weekly-report.html` to `archive/<yyyy-mm-dd>/weekly-report.html` (use today's date).
2. Write a new `output/reports/weekly-report.html`. Use the same layout, sections, charts and appendices as `archive/2026-11-24/2026-11-16-graham-mag7-valuation.html`, the reference format:
   - Visual style: Grafana-style dark dashboard. Copy the `<style>` block and the Google Fonts link from the current `output/reports/weekly-report.html` unchanged (the CSS is also in `scripts/dashboard/grafana_weekly.css`). Charts must use the CSS variables, not fixed colours; the P/V bars use threshold colours (green ≤ 0.70, yellow ≤ 1.00, red above).
   - Your own judgement is needed only for: one-off items to remove from EPS when a stock has a new quarter (set `S.eps` and explain it in the appendix), the analyst 3-year growth estimate `S.g3` (only if it changed in the news), the core-business score `S.core`, and rule D.
   - Rule D: search the news for events whose probability cannot be judged. This is the only web search in the run.
   - Then run `python3 scripts/dashboard/fetch_fundamentals.py --apply`. It writes gaap, period, q, cf, bs, gate/gw, flag/fw (rule C), g = min(15, 0.75 × g3), V = eps × (8.5 + 2g) × 4.4 / Y and buy = 0.70 V into the S block, and the Aaa text. Read its NOTE lines: each is a change since last week to explain in the summary.
   - Keep the per-stock JavaScript data object `S={...}` with the same field names (name, price, eps, g, V, buy, pv, vs, q, cf, bs, total, total1, gate, gw, flag, fw, na, …). Keep the texts `Aaa ต.ค. <year> = <value>%` (use the month actually used) and `ราคาปิด <date and time>`, because scripts read them.
3. Update `data/d_holds.json`. It is a JSON object `{ticker: "one-line Thai reason"}` listing only the stocks currently blocked by rule D.
4. Run `python3 scripts/dashboard/refresh_weekly.py` last of all edits to the report: it writes the live price, P/V, value score and both totals into the S block and the price timestamp into the header. Then run `python3 scripts/dashboard/build_watchlist.py`, then `python3 scripts/dashboard/price_watch.py`. Check that `data/watchlist.json` matches the report's values and buy prices.
5. Commit everything you changed, with a short message, and push to `main`.
6. Finish with a short Thai summary covering:
   - any tier-1 or tier-2 signals
   - stocks within 10% of their buy price
   - changes since last week
   - anything you could not verify

Keep only these two reports in `output/reports/`: `daily-report.html` and `weekly-report.html`. Do not change CLAUDE.md or the backtest scripts (the quarterly files `scripts/backtest/q_<T>.csv` are the exception: `fetch_fundamentals.py` appends new quarters to them).
