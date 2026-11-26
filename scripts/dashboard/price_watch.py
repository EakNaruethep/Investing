#!/usr/bin/env python3
"""Daily report: check rule A (price) only, using the latest close (or the live regular-session
price while the market is open). Pre-market / after-hours trades are shown beside it, not used.

Reads the buy prices from data/watchlist.json (written by the weekly review) and writes
output/reports/daily-report.html, plus one line per stock in data/price_history.csv.
Standard library only.  Run from the repo root:  python3 scripts/dashboard/price_watch.py
"""
import csv, json, os, time, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICT = timezone(timedelta(hours=7))
TH_MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']


def th_time(dt):
    return f'{dt.day} {TH_MON[dt.month - 1]} {dt:%H:%M}'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)['chart']['result'][0]


def quote(sym):
    """Latest trade incl. pre-market/after-hours, its session, previous close and 1-month closes."""
    for attempt in range(3):
        try:
            m = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1m&includePrePost=true')
            d = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d')
            meta = m['meta']
            # Decide on the latest regular-session price (the close outside market hours);
            # pre-market / after-hours trades are shown beside it only.
            price, tsec = float(meta['regularMarketPrice']), int(meta['regularMarketTime'])
            reg = meta['currentTradingPeriod']['regular']
            ts, cl = m.get('timestamp') or [], m['indicators']['quote'][0]['close']
            k = len(ts) - 1
            while k >= 0 and cl[k] is None:
                k -= 1
            ext = None
            if k >= 0 and not (reg['start'] <= ts[k] < reg['end']) and ts[k] > tsec:
                ext = dict(price=float(cl[k]), sess='ก่อนตลาดเปิด' if ts[k] < reg['start'] else 'หลังตลาดปิด',
                           when=th_time(datetime.fromtimestamp(int(ts[k]), ICT)))
            now_s = time.time()
            sess = 'ระหว่างวัน' if reg['start'] <= now_s < reg['end'] and tsec >= reg['start'] else 'ราคาปิด'
            # previous close = last daily close dated before the trade day (exchange time);
            # meta.chartPreviousClose of the 1-day chart is not reliable for this.
            off = timezone(timedelta(seconds=d['meta']['gmtoffset']))
            day = datetime.fromtimestamp(tsec, off).date()
            closes, prev = [], None
            for t, c in zip(d['timestamp'], d['indicators']['quote'][0]['close']):
                if c is None:
                    continue
                closes.append(float(c))
                if datetime.fromtimestamp(t, off).date() < day:
                    prev = float(c)
            return dict(price=price, prev=prev, closes=closes, sess=sess, ext=ext,
                        when=th_time(datetime.fromtimestamp(tsec, ICT)))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def cl(v, a=0.0, b=10.0):
    return max(a, min(b, v))


def fmt(v, d=2):
    return '–' if v is None else f'{v:,.{d}f}'


def pc(v):
    return '–' if v is None else f'{v * 100:+.1f}%'


def spark(c):
    if len(c) < 2:
        return ''
    mn, mx = min(c), max(c)
    mx = mn + 1 if mx == mn else mx
    pts = ' '.join(f'{2 + i * 96 / (len(c) - 1):.1f},{22 - (v - mn) / (mx - mn) * 18:.1f}' for i, v in enumerate(c))
    col = '--up' if c[-1] >= c[0] else '--down'
    return (f"<svg viewBox='0 0 100 26' class='sp' aria-hidden='true' preserveAspectRatio='none'>"
            f"<polygon points='2,26 {pts} 98,26' fill='var({col})' fill-opacity='.15'/>"
            f"<polyline points='{pts}' fill='none' stroke='var({col})' stroke-width='1.4' vector-effect='non-scaling-stroke'/></svg>")


def ext_html(r):
    e = r.get('ext')
    if not e or not r.get('price'):
        return ''
    cc = 'dn' if e['price'] < r['price'] else 'up'
    return (f"<span class='nm'>{e['sess']} {e['when']}: {fmt(e['price'])} "
            f"<span class='{cc}'>{pc(e['price'] / r['price'] - 1)}</span></span>")


def main():
    W = json.load(open(os.path.join(ROOT, 'data', 'watchlist.json'), encoding='utf-8-sig'))
    aaa, yld = float(W['aaa']), float(W['yld'])
    rows = []
    for s in W['stocks']:
        q = quote(s['yahoo']) if s.get('yahoo') else None
        r = dict(t=s['t'], name=s['name'], price=None, chg=None, pv=None, buy=s.get('buy'), gap=None,
                 status='na', why='', spark=[], sess='', when='', ext=None)
        rows.append(r)
        if q is None:
            r['why'] = 'ดึงราคาไม่ได้' if s.get('yahoo') else 'ยังไม่มีราคาซื้อขาย'
            continue
        r.update(price=q['price'], sess=q['sess'], when=q['when'], spark=q['closes'], ext=q['ext'])
        if q['prev']:
            r['chg'] = q['price'] / q['prev'] - 1
        if s.get('na') or not s.get('V'):
            r['why'] = 'EPS ติดลบ ใช้สูตรไม่ได้'
            continue
        V, buy, p = float(s['V']), float(s['buy']), q['price']
        V2 = V * yld / aaa
        buy2 = 0.7 * V2                       # tier 2 uses the actual Aaa
        r['pv'], r['gap'] = p / V, buy / p - 1
        score = float(s['score1']) - 0.25 * float(s['vs']) + 0.25 * cl(10 * (2.0 - p / V2) / 1.3)
        block = ([f"ข้อ C: {s['flagNote']}"] if s.get('flag') else []) + ([s['hold']] if s.get('hold') else [])
        if p <= buy and s.get('gate') and not block:
            r['status'], r['why'] = 't1', 'ผ่านด่านคุณภาพทั้ง 3 · ซื้อเต็ม'
        elif p <= buy2 and score >= 7.5 and not block:
            r['status'], r['why'] = 't2', f'คะแนนเดิม {score:.2f} · ทยอยซื้อ 1/3'
        elif p <= max(buy, buy2):
            r['status'] = 'blocked'
            r['why'] = 'ราคาถึงแล้ว แต่ ' + (' · '.join(block) if block else
                       f"ไม่ผ่านด่านคุณภาพ ({s.get('gateNote')}) และคะแนนเดิม {score:.2f} < 7.5")
        elif p <= 1.10 * buy:
            r['status'] = 'near'
            r['why'] = 'ห่างราคาซื้อไม่เกิน 10%' + (' · ' + ' · '.join(block) if block else
                       (f" · ด่านคุณภาพ: {s.get('gateNote')}" if not s.get('gate') else ''))
        else:
            r['status'] = 'wait'
            r['why'] = ' · '.join(block) if block else (f"ด่านคุณภาพ: {s.get('gateNote')}" if not s.get('gate') else 'รอราคา')
    ivv = quote('IVV')

    now = datetime.now(ICT)
    hist = os.path.join(ROOT, 'data', 'price_history.csv')
    new = not os.path.exists(hist)
    with open(hist, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['date', 'ticker', 'price', 'pv', 'status'])
        for r in rows:
            if r['price']:
                w.writerow([now.strftime('%Y-%m-%d %H:%M'), r['t'], r['price'], round(r['pv'], 3) if r['pv'] else '', r['status']])

    order = dict(t1=0, t2=1, blocked=2, near=3, wait=4, na=5)
    rows.sort(key=lambda r: (order[r['status']], -(r['gap'] if r['gap'] is not None else -99)))
    label = dict(t1='ระดับ 1 ซื้อ', t2='ระดับ 2 ซื้อ 1/3', blocked='ถึงราคา แต่ติดเงื่อนไข', near='ใกล้ราคาซื้อ', wait='รอ', na='ไม่ประเมิน')
    sig = [r for r in rows if r['status'] in ('t1', 't2')]
    if sig:
        banner = "<div class='banner hit'><b>มีสัญญาณซื้อ:</b> " + ', '.join(f"{r['t']} ({label[r['status']]})" for r in sig) + ' · ตรวจข่าวล่าสุดก่อนซื้อ (ข้อ D)</div>'
    else:
        iv = f" (IVV {fmt(ivv['price'])} {pc(ivv['price'] / ivv['prev'] - 1) if ivv['prev'] else ''})" if ivv else ''
        banner = f"<div class='banner'>ยังไม่มีสัญญาณซื้อ · เงินใหม่อยู่ใน IVV{iv}</div>"
    age = (now.replace(tzinfo=None) - datetime.strptime(W['builtAt'], '%Y-%m-%d %H:%M')).days
    stale = f"<div class='banner warn'>ราคาซื้อมาจากรายงานรายสัปดาห์เมื่อ {age} วันก่อน · ควรรันรายงานรายสัปดาห์</div>" if age > 8 else ''
    trs = []
    for r in rows:
        gap = '–' if r['gap'] is None else ('ถึงแล้ว' if r['gap'] >= 0 else pc(r['gap']))
        cc = 'dn' if (r['chg'] or 0) < 0 else 'up'
        trs.append(f"<tr><td><b>{r['t']}</b><span class='nm'>{r['name']}</span></td>"
                   f"<td class='n'>{fmt(r['price'])}<span class='nm {cc}'>{pc(r['chg'])}</span><span class='nm'>{r['sess']} {r['when']}</span>{ext_html(r)}</td>"
                   f"<td>{spark(r['spark'])}</td><td class='n'>{fmt(r['buy'])}</td><td class='n'>{gap}</td>"
                   f"<td class='n'>{fmt(r['pv']) + '×' if r['pv'] else '–'}</td>"
                   f"<td><span class='pill p-{r['status']}'>{label[r['status']]}</span><span class='why'>{r['why']}</span></td></tr>")
    # Grafana-style stat panels and bar gauge (same data as the table: buy price / price today)
    cnt = {k: [r['t'] for r in rows if r['status'] == k] for k in label}
    def stat(title, names, color):
        return (f"<div class='panel stat'><div class='pt'>{title}</div><div class='v' style='color:{color if names else 'var(--muted)'}'>{len(names)}</div>"
                f"<div class='s'>{', '.join(names) or '—'}</div></div>")
    ivv_s = (f"<div class='panel stat'><div class='pt'>IVV (S&amp;P 500)</div><div class='v' style='color:var(--accent);font-size:30px;padding:4px 0'>{fmt(ivv['price'])}</div>"
             f"<div class='s' style='color:var({'--up' if (ivv['prev'] and ivv['price'] >= ivv['prev']) else '--down'})'>{pc(ivv['price'] / ivv['prev'] - 1) if ivv['prev'] else ''}</div></div>") if ivv else ''
    stats = ("<div class='stats'>" + stat('ระดับ 1 ซื้อเต็ม', cnt['t1'], 'var(--t1)') + stat('ระดับ 2 ซื้อ 1/3', cnt['t2'], 'var(--t2)')
             + stat('ถึงราคา แต่ติดเงื่อนไข', cnt['blocked'], 'var(--bl)') + stat('ใกล้ราคาซื้อ (≤10%)', cnt['near'], 'var(--nr)') + ivv_s + "</div>")
    gcol = dict(t1='var(--t1)', t2='var(--t2)', blocked='var(--bl)', near='var(--nr)', wait='var(--accent)', na='var(--wt)')
    gs = []
    for r in rows:
        if r['gap'] is None:
            continue
        ratio = r['gap'] + 1          # buy / price: 100% = price has reached the buy price
        gs.append(f"<div class='g'><b>{r['t']}</b><div class='gb'><i style='width:{min(ratio, 1) * 100:.1f}%;background:{gcol[r['status']]}'></i></div>"
                  f"<span class='gv'>{ratio * 100:.0f}%</span></div>")
    gauge = ("<div class='panel'><div class='pt'>ความใกล้ราคาซื้อ (ราคาซื้อ ÷ ราคาวันนี้ · 100% = ถึงราคาซื้อ)</div><div class='gauges'>" + ''.join(gs) + "</div>"
             "<div class='legend'><span><i style='background:var(--t1)'></i>ระดับ 1</span><span><i style='background:var(--t2)'></i>ระดับ 2</span>"
             "<span><i style='background:var(--bl)'></i>ถึงราคา แต่ติดเงื่อนไข</span><span><i style='background:var(--nr)'></i>ใกล้ราคาซื้อ</span>"
             "<span><i style='background:var(--accent)'></i>รอ</span><span>เส้นประ = ห่าง 10%</span></div></div>")
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily.css'), encoding='utf-8').read()
    html = f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>รายงานราคารายวัน</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=IBM+Plex+Sans+Thai:wght@400;500;600&family=Roboto+Mono&display=swap"><style>{css}</style></head><body><div class="wrap">
<header><div class="crumb">▦ Dashboards / Investing /</div><h1>รายงานราคารายวัน</h1><div class="sub">อัปเดต {th_time(now)} (เวลาไทย) · ตัดสินด้วยราคาปิดล่าสุด (หรือราคาระหว่างวันถ้าตลาดเปิดอยู่) จาก Yahoo ณ นาทีที่รัน · ราคาก่อนตลาดเปิด/หลังตลาดปิดแสดงไว้ใต้ราคาเป็นข้อมูลเสริม ไม่ใช้ตัดสิน · % เทียบราคาปิดวันก่อน · ราคาซื้อจากรายงานรายสัปดาห์ {W['builtAt']} · Aaa {aaa}%</div></header>
{banner}{stale}
{stats}
{gauge}
<div class="panel"><div class="pt">ราคาเทียบราคาซื้อ</div><div class="scroll"><table><thead><tr><th>หุ้น</th><th style="text-align:right">ราคา</th><th>1 เดือน</th><th style="text-align:right">ราคาซื้อ</th><th style="text-align:right">ต้องลงอีก</th><th style="text-align:right">ราคา/มูลค่า</th><th>สถานะ</th></tr></thead><tbody>
{chr(10).join(trs)}
</tbody></table></div></div>
<footer>รายงานนี้ดูแค่ข้อ A (ราคา) ส่วนข้อ B, C, D ใช้ผลจากรายงานรายสัปดาห์ (weekly-report.html) · ระดับ 2 ใช้ราคาซื้อที่คิดด้วย Aaa จริงและคะแนนเดิมที่ราคาวันนี้ · "ต้องลงอีก" = ราคาซื้อ ÷ ราคาวันนี้ − 1 · ไม่ใช่คำแนะนำการลงทุน</footer>
</div></body></html>"""
    out = os.path.join(ROOT, 'output', 'reports', 'daily-report.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    for r in rows:
        print(f"{r['t']:<5} {fmt(r['price']):>9} {pc(r['chg']):>7} {r['status']:<8} {r['why']}")
    print('wrote', out)


if __name__ == '__main__':
    main()
