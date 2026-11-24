#!/usr/bin/env python3
"""Daily report: check rule A (price) only, using the latest traded price at the minute it runs.

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
            ts, cl = m.get('timestamp') or [], m['indicators']['quote'][0]['close']
            k = len(ts) - 1
            while k >= 0 and cl[k] is None:
                k -= 1
            if k >= 0:
                price, tsec = float(cl[k]), int(ts[k])
            else:
                price, tsec = float(m['meta']['regularMarketPrice']), int(m['meta']['regularMarketTime'])
            reg = m['meta']['currentTradingPeriod']['regular']
            if abs(tsec - reg['end']) <= 60:
                sess = 'ราคาปิด'
            elif tsec < reg['start']:
                sess = 'ก่อนตลาดเปิด'
            elif tsec < reg['end']:
                sess = 'ระหว่างวัน'
            else:
                sess = 'หลังตลาดปิด'
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
            return dict(price=price, prev=prev, closes=closes, sess=sess,
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
    return f"<svg viewBox='0 0 100 26' class='sp' aria-hidden='true'><polyline points='{pts}' fill='none' stroke='var({col})' stroke-width='1.6'/></svg>"


def main():
    W = json.load(open(os.path.join(ROOT, 'data', 'watchlist.json'), encoding='utf-8-sig'))
    aaa, yld = float(W['aaa']), float(W['yld'])
    rows = []
    for s in W['stocks']:
        q = quote(s['yahoo']) if s.get('yahoo') else None
        r = dict(t=s['t'], name=s['name'], price=None, chg=None, pv=None, buy=s.get('buy'), gap=None,
                 status='na', why='', spark=[], sess='', when='')
        rows.append(r)
        if q is None:
            r['why'] = 'ดึงราคาไม่ได้' if s.get('yahoo') else 'ยังไม่มีราคาซื้อขาย'
            continue
        r.update(price=q['price'], sess=q['sess'], when=q['when'], spark=q['closes'])
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
                   f"<td class='n'>{fmt(r['price'])}<span class='nm {cc}'>{pc(r['chg'])}</span><span class='nm'>{r['sess']} {r['when']}</span></td>"
                   f"<td>{spark(r['spark'])}</td><td class='n'>{fmt(r['buy'])}</td><td class='n'>{gap}</td>"
                   f"<td class='n'>{fmt(r['pv']) + '×' if r['pv'] else '–'}</td>"
                   f"<td><span class='pill p-{r['status']}'>{label[r['status']]}</span><span class='why'>{r['why']}</span></td></tr>")
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily.css'), encoding='utf-8').read()
    html = f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>รายงานราคารายวัน</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;600&family=IBM+Plex+Mono&display=swap"><style>{css}</style></head><body><div class="wrap">
<header><h1>รายงานราคารายวัน</h1><div class="sub">อัปเดต {th_time(now)} (เวลาไทย) · ราคาซื้อขายล่าสุด ณ นาทีที่รัน รวมช่วงก่อนตลาดเปิดและหลังตลาดปิด (Yahoo) · % เทียบราคาปิดวันก่อน · ราคาซื้อจากรายงานรายสัปดาห์ {W['builtAt']} · Aaa {aaa}%</div></header>
{banner}{stale}
<div class="scroll"><table><thead><tr><th>หุ้น</th><th style="text-align:right">ราคา</th><th>1 เดือน</th><th style="text-align:right">ราคาซื้อ</th><th style="text-align:right">ต้องลงอีก</th><th style="text-align:right">ราคา/มูลค่า</th><th>สถานะ</th></tr></thead><tbody>
{chr(10).join(trs)}
</tbody></table></div>
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
