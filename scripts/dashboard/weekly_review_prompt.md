# Weekly report (every Monday 08:30 Thai time)

Weekly full review of Eak's watchlist with the two-tier Graham buy rules. Work in the root of this repository and follow CLAUDE.md exactly (method, weights, rules A–D). Write the report in Thai. This analyses a method; it is not investment advice, and never execute trades.

Stocks: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, TSM (ADR, USD) and SpaceX (SPCX).

**Every number must be the latest available when the run starts.** Prices are the last traded price at that minute, including pre-market and after-hours, with their time and session. Use Yahoo's chart API `range=1d&interval=1m&includePrePost=true` and take the last non-null close. Compute % change against the previous trading day's close from `range=1mo&interval=1d`. Do not use `meta.chartPreviousClose`. Use the latest financial statements and news.

Steps
1. Copy the current `output/reports/weekly-report.html` to `archive/<yyyy-mm-dd>/weekly-report.html` (use today's date).
2. Write a new `output/reports/weekly-report.html`. Use the same layout, sections, charts and appendices as `archive/2026-11-24/2026-11-16-graham-mag7-valuation.html`, the reference format:
   - Visual style: Grafana-style dark dashboard. Copy the `<style>` block and the Google Fonts link from the current `output/reports/weekly-report.html` unchanged (the CSS is also in `scripts/dashboard/grafana_weekly.css`). Charts must use the CSS variables, not fixed colours; the P/V bars use threshold colours (green ≤ 0.70, yellow ≤ 1.00, red above).
   - Prices with their timestamps, and Moody's Aaa (latest monthly value of the FRED series AAA). Y = max(Aaa, 4.4%).
   - TTM EPS with one-off items removed, explaining each adjustment in the appendix. g = min(15%, 0.75 × 3-year growth). V = EPS × (8.5 + 2g) × 4.4 / Y. Buy price = 0.70 V.
   - Quality gates q, cf and bs from the latest 4 quarters, and the old weighted score (25/25/20/15/15).
   - Rule C: EPS growth over 40%/yr on BOTH the 3-year and 5-year CAGR, or a loss in the last 3 years.
   - Rule D: search the news for events whose probability cannot be judged.
   - Keep the per-stock JavaScript data object `S={...}` with the same field names (name, price, eps, g, V, buy, pv, vs, q, cf, bs, total, total1, gate, gw, flag, fw, na, …). Keep the texts `Aaa ต.ค. <year> = <value>%` (use the month actually used) and `ราคาปิด <date and time>`, because scripts read them.
3. Update `data/d_holds.json`. It is a JSON object `{ticker: "one-line Thai reason"}` listing only the stocks currently blocked by rule D.
4. Run `python3 scripts/dashboard/refresh_weekly.py` last of all edits to the report: it writes the live price, P/V, value score and both totals into the S block and the price timestamp into the header. Then run `python3 scripts/dashboard/build_watchlist.py`, then `python3 scripts/dashboard/price_watch.py`. Check that `data/watchlist.json` matches the report's values and buy prices.
5. Commit everything you changed, with a short message, and push to `main`.
6. Finish with a short Thai summary covering:
   - any tier-1 or tier-2 signals
   - stocks within 10% of their buy price
   - changes since last week
   - anything you could not verify

Keep only these two reports in `output/reports/`: `daily-report.html` and `weekly-report.html`. Do not change CLAUDE.md or the backtest scripts.
