# Daily report (Tuesday–Saturday 08:30 Thai time)

In the root of this repository:

1. Run `python3 scripts/dashboard/price_watch.py`. It needs no extra packages. It fetches the latest close (or live regular-session price) from Yahoo, with pre-market/after-hours shown beside it only, checks them against the buy prices in `data/watchlist.json` (rule A only) and rewrites `output/reports/daily-report.html`. It also adds rows to `data/price_history.csv`.
2. If the script fails, fix only what is needed to make it run, such as a network retry. Do not change the buy prices or the rules.
3. Commit `output/reports/daily-report.html` and `data/price_history.csv` with the message `Daily report <yyyy-mm-dd>` and push to `main`.
4. Reply with 3–5 lines in Thai:
   - any tier-1 or tier-2 signal
   - stocks within 10% of their buy price
   - a warning if `data/watchlist.json` is more than 8 days old

Do no other analysis; this run should stay short.
