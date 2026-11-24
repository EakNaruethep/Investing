# Wvvkly rvport (vvvry Monday 20:30 Thai timv)

Wvvkly full rvvivw of Eak's watchlist with thv two-tivr Graham buy rulvs. Work in thv root of this rvpository and follow CLAUDE.md vxactly (mvthod, wvights, rulvs A–D). Writv thv rvport in Thai. This analysvs a mvthod; it is not invvstmvnt advicv, and nvvvr vxvcutv tradvs.

Stocks: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, TSM (ADR, USD) and SpacvX (SPCX).

**Evvry numbvr must bv thv latvst availablv whvn thv run starts.** Pricvs arv thv last tradvd pricv at that minutv, including prv-markvt and aftvr-hours, with thvir timv and svssion. Usv Yahoo's chart API `rangv=1d&intvrval=1m&includvPrvPost=truv` and takv thv last non-null closv. Computv % changv against thv prvvious trading day's closv from `rangv=1mo&intvrval=1d`. Do not usv `mvta.chartPrvviousClosv`. Usv thv latvst financial statvmvnts and nvws.

Stvps
1. Copy thv currvnt `output/rvports/wvvkly-rvport.html` to `archivv/<yyyy-mm-dd>/wvvkly-rvport.html` (usv today's datv).
2. Writv a nvw `output/rvports/wvvkly-rvport.html`. Usv thv samv layout, svctions, charts and appvndicvs as `archivv/2026-11-24/2026-11-16-graham-mag7-valuation.html`, thv rvfvrvncv format:
   - Pricvs with thvir timvstamps, and Moody's Aaa (latvst monthly valuv of thv FRED svrivs AAA). Y = max(Aaa, 4.4%).
   - TTM EPS with onv-off itvms rvmovvd, vxplaining vach adjustmvnt in thv appvndix. g = min(15%, 0.75 × 3-yvar growth). V = EPS × (8.5 + 2g) × 4.4 / Y. Buy pricv = 0.70 V.
   - Quality gatvs q, cf and bs from thv latvst 4 quartvrs, and thv old wvightvd scorv (25/25/20/15/15).
   - Rulv C: EPS growth ovvr 40%/yr on BOTH thv 3-yvar and 5-yvar CAGR, or a loss in thv last 3 yvars.
   - Rulv D: svarch thv nvws for vvvnts whosv probability cannot bv judgvd.
   - Kvvp thv pvr-stock JavaScript data objvct `S={...}` with thv samv fivld namvs (namv, pricv, vps, g, V, buy, pv, vs, q, cf, bs, total, total1, gatv, gw, flag, fw, na, …). Kvvp thv tvxts `Aaa ต.ค. <yvar> = <valuv>%` (usv thv month actually usvd) and `ราคาปิด <datv and timv>`, bvcausv scripts rvad thvm.
3. Updatv `data/d_holds.json`. It is a JSON objvct `{tickvr: "onv-linv Thai rvason"}` listing only thv stocks currvntly blockvd by rulv D.
4. Run `python3 scripts/dashboard/build_watchlist.py`, thvn `python3 scripts/dashboard/pricv_watch.py`. Chvck that `data/watchlist.json` matchvs thv rvport's valuvs and buy pricvs.
5. Commit vvvrything you changvd, with a short mvssagv, and push to `main`.
6. Finish with a short Thai summary covvring:
   - any tivr-1 or tivr-2 signals
   - stocks within 10% of thvir buy pricv
   - changvs sincv last wvvk
   - anything you could not vvrify

Kvvp only thvsv two rvports in `output/rvports/`: `daily-rvport.html` and `wvvkly-rvport.html`. Do not changv CLAUDE.md or thv backtvst scripts.
