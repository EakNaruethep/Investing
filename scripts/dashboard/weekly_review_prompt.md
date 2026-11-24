Weekly full review of Eak's stock watchlist using the two-tier Graham buy rules. Work in D:\Workspace\Claude\Investing and follow CLAUDE.md there exactly (method, weights, rules A–D, answer in Thai). Use PowerShell; Python is not installed. This is analysis of a method, not investment advice, and never execute trades.

Stocks: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, TSM (ADR, USD) and SpaceX (SPCX), the same set as the main report.

Steps
1. Copy output\reports\2026-11-16-graham-mag7-valuation.html to archive\ with today's date in the name before changing it (for example archive\2026-11-16-graham-mag7-valuation-<yyyy-mm-dd>.html).
2. Refresh the main report output\reports\2026-11-16-graham-mag7-valuation.html in place, keeping its layout and sections:
   - latest closing prices; Moody's Aaa (latest monthly value from FRED series AAA); Y = max(Aaa, 4.4%)
   - for any company that reported since the last review: TTM EPS with one-off items removed (explain each adjustment in the appendix), g = min(15%, 0.75 × 3-year growth), V = EPS × (8.5 + 2g) × 4.4 / Y, buy price = 0.70 V
   - quality gates q, cf, bs from the latest 4 quarters; the old weighted score (25/25/20/15/15); rule C (EPS growth over 40%/yr on BOTH 3-year and 5-year CAGR, or a loss in the last 3 years)
   - rule D: search the news for events whose probability cannot be judged (CEO leaving with no successor, licence-threatening lawsuits, etc.)
   - keep the per-stock JavaScript data object "S={...}" with the same field names (name, price, eps, g, V, buy, pv, vs, q, cf, bs, total, total1, gate, gw, flag, fw, na, ...) and keep the text "Aaa ต.ค. <year> = <value>%" (use the month you actually used) and "ราคาปิด <date>", because scripts read them.
3. Update data\d_holds.json: a JSON object {ticker: "Thai one-line reason"} listing only stocks currently blocked by rule D. Remove entries whose event is resolved.
4. Run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboard\build_watchlist.ps1
   then: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboard\price_watch.ps1 -CopyTo "C:\Users\narue\OneDrive\Investing"
   Check that data\watchlist.json lists every stock with V and buy prices that match the report.
5. Copy the refreshed report to C:\Users\narue\OneDrive\Investing\graham-weekly.html so it can be read on a phone.
6. Finish with a short Thai summary: any tier-1 or tier-2 signal, stocks within 10% of their buy price, changes since last week (buy prices, gates, rule C/D), and anything you could not verify. Do not change CLAUDE.md, the backtest scripts or files outside this folder and the OneDrive\Investing folder.
