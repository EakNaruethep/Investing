#!/usr/bin/env python3
"""Weekly step: fetch every outside number the review needs, except news, so the model does not.

Sources (all allowed in the cloud environment):
  * FRED  series AAA (Moody's Aaa)                    -> data/macro/AAA.csv
  * Yahoo fundamentals-timeseries (latest quarters)   -> appended to scripts/backtest/q_<T>.csv
  * SEC   companyconcept, annual diluted EPS (10-K/20-F) for the 5-year growth check
  * Yahoo chart: splits (to adjust old SEC EPS) and TWD=X (TSM is reported in TWD)

It then works out, per stock, from the last 4 quarters:
  TTM GAAP EPS (USD; TSM per ADR = 5 shares), EPS CAGR over 3 and 5 years, loss in the last 3 years,
  the quality gates q, cf, bs exactly as CLAUDE.md defines them, and the FCF of the last 5 quarters.
Everything is written to data/fundamentals.json and printed as one short table.

What stays with the model: news (rule D), one-off adjustments to EPS (S.eps), the analyst
3-year growth estimate (S.g3, Yahoo's estimates need a login cookie) and the core-business score.

  python3 scripts/dashboard/fetch_fundamentals.py           fetch + table
  python3 scripts/dashboard/fetch_fundamentals.py --apply   also write the numbers into the S={...}
        block of output/reports/weekly-report.html: gaap, period, q, cf, bs, gate/gw (formula),
        flag/fw (rule C), g = min(15, 0.75*g3), V and buy from S.eps, and the Aaa text.
        Then run refresh_weekly.py for prices and scores.
Standard library only. Run from the repo root.
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from price_watch import ROOT, ICT, TH_MON  # noqa: E402

UA_Y = {'User-Agent': 'Mozilla/5.0'}
UA_SEC = {'User-Agent': 'Investing research script research@example.com'}
CIK = {'AAPL': 320193, 'MSFT': 789019, 'GOOGL': 1652044, 'AMZN': 1018724, 'META': 1326801,
       'NVDA': 1045810, 'TSLA': 1318605, 'TSM': 1046179}
ADR = {'TSM': 5}            # common shares per ADR
COLS = ['end', 'rev', 'op', 'ni', 'eps', 'ocf', 'capex', 'fcf', 'cash', 'debt', 'eq']
YT = {'rev': 'TotalRevenue', 'op': 'OperatingIncome', 'ni': 'NetIncomeCommonStockholders', 'eps': 'DilutedEPS',
      'sh': 'DilutedAverageShares', 'ocf': 'OperatingCashFlow', 'capex': 'CapitalExpenditure', 'fcf': 'FreeCashFlow',
      'cash': 'CashCashEquivalentsAndShortTermInvestments', 'debt': 'TotalDebt', 'eq': 'StockholdersEquity'}


def get(url, hdr=UA_Y, raw=False):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=30) as r:
                b = r.read()
                return b.decode('utf-8') if raw else json.loads(b)
        except Exception as e:
            err = e
            time.sleep(2 * (attempt + 1))
    print(f'  ! fetch failed {url[:90]}: {err!r}')
    return None


def d2o(s):
    return datetime.strptime(s[:10], '%Y-%m-%d').toordinal()


# ---------- Aaa ----------
def fetch_aaa():
    p = os.path.join(ROOT, 'data', 'macro', 'AAA.csv')
    txt = get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=AAA', {'User-Agent': 'curl/8.5.0'}, raw=True)
    if txt and txt.count('\n') > 100:
        open(p, 'w', encoding='utf-8').write(txt if txt.endswith('\n') else txt + '\n')
    rows = [r for r in csv.reader(open(p, encoding='utf-8')) if r and r[0][:1].isdigit() and r[1] not in ('', '.')]
    d, v = rows[-1][0], float(rows[-1][1])
    return {'month': d[:7], 'value': v, 'y': max(v, 4.4), 'fresh': bool(txt)}


# ---------- quarterly statements ----------
def read_q(t):
    p = os.path.join(ROOT, 'scripts', 'backtest', f'q_{t}.csv')
    if not os.path.exists(p):
        return p, []
    rows = []
    for r in csv.DictReader(open(p, encoding='utf-8-sig')):
        r = {k.strip().lower(): v for k, v in r.items()}
        rows.append({k: (r.get(k) if k == 'end' else (float(r[k]) if r.get(k) not in (None, '') else None)) for k in COLS})
    return p, rows


def yahoo_quarters(t):
    now = int(time.time())
    types = ','.join('quarterly' + v for v in YT.values())
    j = get(f'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{t}'
            f'?type={types}&period1={now - 3 * 366 * 86400}&period2={now}')
    if not j:
        return [], ''
    inv = {v: k for k, v in YT.items()}
    q, cur = {}, ''
    for x in j['timeseries']['result']:
        typ = x['meta']['type'][0]
        for v in x.get(typ) or []:
            if v and v.get('reportedValue'):
                q.setdefault(v['asOfDate'], {})[inv[typ[9:]]] = v['reportedValue']['raw']
                cur = v.get('currencyCode') or cur
    out = []
    for d in sorted(q):
        r = q[d]
        if r.get('rev') is None or r.get('ni') is None or r.get('ocf') is None:
            continue
        eps = r.get('eps') or (r['ni'] / r['sh'] if r.get('sh') else None)
        if eps is not None and t in ADR and r.get('eps'):
            eps /= ADR[t]                       # Yahoo gives TSM EPS per ADR; the csv keeps it per share
        capex = r.get('capex') or 0.0
        fcf = r['fcf'] if r.get('fcf') is not None else r['ocf'] + capex
        m = lambda k: None if r.get(k) is None else round(r[k] / 1e6, 0)
        out.append({'end': d, 'rev': m('rev'), 'op': m('op'), 'ni': m('ni'), 'eps': None if eps is None else round(eps, 2),
                    'ocf': m('ocf'), 'capex': round(capex / 1e6, 0), 'fcf': round(fcf / 1e6, 0),
                    'cash': m('cash'), 'debt': m('debt') if r.get('debt') is not None else 0.0, 'eq': m('eq')})
    return out, cur


def merge_q(t):
    p, rows = read_q(t)
    new, cur = yahoo_quarters(t)
    last = rows[-1]['end'] if rows else '0000'
    added = [r for r in new if r['end'] > last and (not rows or d2o(r['end']) - d2o(last) > 45)]
    if added:
        rows += added
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(COLS)
            for r in rows:
                w.writerow([r['end']] + ['' if r[k] is None else (f'{r[k]:.2f}' if k == 'eps' else f'{r[k]:.0f}') for k in COLS[1:]])
    return rows, [r['end'] for r in added], cur


# ---------- annual EPS (SEC) and splits ----------
def splits(t):
    j = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=20y&interval=3mo&events=split')
    ev = ((j or {}).get('chart', {}).get('result') or [{}])[0].get('events', {}).get('splits', {})
    return [(datetime.utcfromtimestamp(s['date']).date().isoformat(), s['numerator'] / s['denominator']) for s in ev.values()]


def sec_annual_eps(t, spl):
    if t not in CIK:
        return {}
    tax, tag = ('ifrs-full', 'DilutedEarningsLossPerShare') if t == 'TSM' else ('us-gaap', 'EarningsPerShareDiluted')
    j = get(f'https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK[t]:010d}/{tax}/{tag}.json', UA_SEC)
    if not j:
        return {}
    out = {}
    want = 'TWD/shares' if t == 'TSM' else 'USD/shares'
    for u, unit in j['units'].items():
        if u != want:
            continue
        for x in unit:
            if x.get('form', '').split('/')[0] not in ('10-K', '20-F') or 'start' not in x:
                continue
            if not 330 <= d2o(x['end']) - d2o(x['start']) <= 380:
                continue
            f = 1.0
            for sd, r in spl:                  # adjust to today's share count; skip filings made after the split
                if sd > x['end'] and x['filed'] < sd:
                    f *= r
            out[x['end']] = round(x['val'] / f, 4)   # latest filing wins (restated values)
    return out


def fx_twd():
    j = get('https://query1.finance.yahoo.com/v8/finance/chart/TWD=X?range=5d&interval=1d')
    return float(j['chart']['result'][0]['meta']['regularMarketPrice']) if j else 32.9


# ---------- metrics ----------
def cl(v):
    return max(0.0, min(10.0, v))


def half(v):
    return round(v * 2) / 2


def cagr(a, b, n):
    return None if a is None or b is None or a <= 0 or b <= 0 else ((b / a) ** (1 / n) - 1) * 100


def metrics(t, rows, ann, fx):
    k4 = rows[-4:]
    s = lambda k, rr=k4: sum((r[k] or 0) for r in rr)
    rev, op, ni, ocf, fcf = s('rev'), s('op'), s('ni'), s('ocf'), s('fcf')
    last = rows[-1]
    conv = (ADR.get(t, 1) / fx) if t == 'TSM' else 1.0
    ttm = lambda i: sum(r['eps'] for r in rows[i - 3:i + 1]) if i >= 3 and all(r['eps'] is not None for r in rows[i - 3:i + 1]) else None
    eps_now = ttm(len(rows) - 1)
    end = last['end']

    def back(years):
        i = len(rows) - 1 - 4 * years
        if i >= 3 and abs(d2o(end) - d2o(rows[i]['end']) - 365.25 * years) < 60:
            return ttm(i), f"TTM {rows[i]['end'][:7]}"
        target = d2o(end) - 365.25 * years
        c = [(abs(d2o(e) - target), e) for e in ann]
        if c and min(c)[0] < 200:
            e = min(c)[1]
            return ann[e], f'FY {e[:7]}'
        return None, ''
    e3, b3 = back(3)
    e5, b5 = back(5)
    g3h, g5h = cagr(e3, eps_now, 3), cagr(e5, eps_now, 5)
    loss = any((r['ni'] or 0) < 0 for r in rows[-12:]) or (eps_now is not None and eps_now < 0) \
        or any(v < 0 for e, v in ann.items() if d2o(end) - d2o(e) < 3 * 365 + 60)
    opm, roe = op / rev if rev else 0, ni / last['eq'] if last['eq'] else 0
    q = (cl(opm / .40 * 10) + cl(roe / .35 * 10)) / 2
    cf = (cl(fcf / ni * 10) if ni > 0 else 0) / 2 + cl(fcf / rev / .25 * 10) / 2 if rev else 0
    netdebt = (last['debt'] or 0) - (last['cash'] or 0)
    bs = 10.0 if netdebt <= 0 else (cl(10 - 2.5 * netdebt / ocf) if ocf > 0 else 0.0)
    streak = 0
    for r in reversed(rows[-5:]):
        if r['fcf'] >= 0:
            break
        streak += 1
    fail = [n for n, v, lim in (('q', q, 6), ('cf', cf, 5), ('bs', bs, 5)) if v < lim]
    ruleC = loss or (g3h is not None and g5h is not None and g3h > 40 and g5h > 40)
    return dict(end=end, ttm_eps=None if eps_now is None else round(eps_now * conv, 2), eps_local=eps_now,
                g3_hist=None if g3h is None else round(g3h, 1), base3=b3, g5_hist=None if g5h is None else round(g5h, 1), base5=b5,
                loss3y=loss, opm=round(opm * 100, 1), roe=round(roe * 100, 1), fcf_ni=round(fcf / ni, 2) if ni else None,
                fcfm=round(fcf / rev * 100, 1) if rev else None, netdebt=netdebt, ocf=ocf,
                q=half(q), cf=half(cf), bs=half(bs), gate=not fail, gate_fail=fail, fcf_neg_streak=streak,
                fcf5=[[r['end'], r['ocf'], r['capex'], r['fcf']] for r in rows[-5:]], ruleC=ruleC)


def th_month(ym):
    y, m = ym.split('-')
    return f'{TH_MON[int(m) - 1]} {y}'


def apply(F, aaa):
    from refresh_weekly import s_block, DST
    h = open(DST, encoding='utf-8').read()
    a, b, S = s_block(h)
    Y = aaa['y']
    notes = []
    for t, d in S.items():
        m = F.get(t)
        if not m:
            continue
        if m['new_quarters']:
            notes.append(f"{t}: new quarter {', '.join(m['new_quarters'])}: GAAP TTM EPS {d.get('gaap')} -> {m['ttm_eps']}; review one-offs and set S.eps (now {d.get('eps')})")
        if m['ttm_eps'] is not None:
            d['gaap'] = m['ttm_eps']
        d['period'] = f"TTM ถึง {th_month(m['end'][:7])}"
        d['q'], d['cf'], d['bs'] = m['q'], m['cf'], m['bs']
        gw = 'ผ่าน' if m['gate'] else 'ไม่ผ่าน: ' + ' · '.join(
            {'q': f"margin/ROE ต่ำ (q {m['q']})", 'cf': f"กระแสเงินสดอ่อน (cf {m['cf']})", 'bs': f"หนี้สูง (bs {m['bs']})"}[k] for k in m['gate_fail'])
        if m['fcf_neg_streak']:
            gw += f" · FCF ติดลบ {m['fcf_neg_streak']} ไตรมาสล่าสุด"
        if bool(d.get('gate')) != m['gate']:
            notes.append(f"{t}: gate {'pass' if d.get('gate') else 'fail'} -> {'pass' if m['gate'] else 'fail'} by formula ({gw})")
        d['gate'], d['gw'] = int(m['gate']), gw
        if m['ruleC']:
            fw = 'ขาดทุนใน 3 ปีล่าสุด' if m['loss3y'] else f"EPS โต {m['g3_hist']:.0f}%/ปี (3 ปี) และ {m['g5_hist']:.0f}%/ปี (5 ปี)"
        else:
            fw = ''
        if bool(d.get('flag')) != m['ruleC']:
            notes.append(f"{t}: rule C {bool(d.get('flag'))} -> {m['ruleC']} ({fw or 'ผ่าน'})")
        d['flag'], d['fw'] = int(m['ruleC']), fw
        if d.get('na') or not d.get('eps') or d['eps'] <= 0:
            continue
        d['g'] = round(min(15.0, 0.75 * float(d.get('g3') or 0)), 1)
        d['V'] = round(d['eps'] * (8.5 + 2 * d['g']) * 4.4 / Y, 2)
        d['buy'] = round(0.7 * d['V'], 2)
    h = h[:a] + json.dumps(S, ensure_ascii=False, separators=(',', ':')) + h[b:]
    h = re.sub(r'Aaa [^\s<]+ \d{4} = [\d.]+%', f"Aaa {th_month(aaa['month'])} = {aaa['value']}%", h)
    open(DST, 'w', encoding='utf-8').write(h)
    print('applied to', DST)
    for n in notes:
        print('  NOTE', n)


def main():
    aaa = fetch_aaa()
    fx = fx_twd()
    out = {'asof': datetime.now(ICT).strftime('%Y-%m-%d %H:%M'), 'aaa': aaa, 'twd_per_usd': fx, 't': {}}
    print(f"Aaa {aaa['month']} = {aaa['value']}% (Y = {aaa['y']}%){'' if aaa['fresh'] else '  ! FRED unreachable, last saved value'} · TWD/USD {fx:.2f}")
    print(f"{'T':<5} {'end':<10} {'new':<4} {'EPS':>7} {'g3h':>6} {'g5h':>6} {'opm':>5} {'roe':>5} {'q':>4} {'cf':>4} {'bs':>4} gate  C  FCF-")
    for t in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'TSM', 'SPCX']:
        rows, added, cur = merge_q(t)
        if len(rows) < 4:
            print(f'{t:<5} not enough quarterly data ({len(rows)} quarters)')
            continue
        m = metrics(t, rows, sec_annual_eps(t, splits(t)), fx)
        m['new_quarters'] = added
        out['t'][t] = m
        f = lambda v, w=6: f'{v:>{w}.1f}' if isinstance(v, (int, float)) else f"{'–':>{w}}"
        print(f"{t:<5} {m['end']:<10} {len(added):<4} {f(m['ttm_eps'], 7)} {f(m['g3_hist'])} {f(m['g5_hist'])} {f(m['opm'], 5)} {f(m['roe'], 5)} "
              f"{m['q']:>4} {m['cf']:>4} {m['bs']:>4} {'pass' if m['gate'] else 'FAIL'}  {'Y' if m['ruleC'] else '-'}  {m['fcf_neg_streak']}")
    json.dump(out, open(os.path.join(ROOT, 'data', 'fundamentals.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote data/fundamentals.json')
    if '--apply' in sys.argv:
        apply(out['t'], aaa)


if __name__ == '__main__':
    main()
