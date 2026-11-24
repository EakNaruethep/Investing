#!/usr/bin/env python3
"""Weekly step: refresh output/reports/weekly-report.html with the latest traded prices.

The weekly report keeps the layout of archive/2026-11-24/2026-11-16-graham-mag7-valuation.html.
This script only updates what depends on price: in the S={...} data block it rewrites price,
pv (price / V), vs (valuation score), total (weights 40/20/15/15/10) and total1 (old weights
25/25/20/15/15), and it rewrites the price timestamp in the header. EPS, g, V, the buy price,
the quality gates and rules C and D are not touched here: the weekly review updates them in
the S block when new results, a new Aaa or news arrive, before running this script.

Template: the current weekly-report.html if it has an S block, otherwise the 16 Nov report.
Run from the repo root:  python3 scripts/dashboard/refresh_weekly.py
"""
import json, os, re, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from price_watch import quote, ICT, TH_MON, ROOT  # noqa: E402

DST = os.path.join(ROOT, 'output', 'reports', 'weekly-report.html')
BASE = os.path.join(ROOT, 'archive', '2026-11-24', '2026-11-16-graham-mag7-valuation.html')


def s_block(h):
    i = h.find('S={')
    if i < 0:
        return None, None, None
    i += 2
    depth = 0
    for k in range(i, len(h)):
        if h[k] == '{':
            depth += 1
        elif h[k] == '}':
            depth -= 1
            if depth == 0:
                return i, k + 1, json.loads(h[i:k + 1])
    return None, None, None


def main():
    src = DST if os.path.exists(DST) and 'S={' in open(DST, encoding='utf-8').read() else BASE
    h = open(src, encoding='utf-8').read()
    a, b, S = s_block(h)
    if S is None:
        sys.exit(f'No S={{...}} block in {src}')
    now = datetime.now(ICT)
    stamp = f'{now.day} {TH_MON[now.month - 1]} {now.year} {now:%H:%M} น.'
    failed = []
    for t, d in S.items():
        q = quote(t)
        if not q:
            failed.append(t)
            continue
        d['price'] = round(q['price'], 2)
        d['asof'] = f"{q['sess']} {q['when']}"
        V = d.get('V')
        if V and not d.get('na'):
            d['pv'] = round(d['price'] / V, 2)
            d['vs'] = round(min(10.0, max(0.0, (2.0 - d['pv']) / 1.3 * 10)), 1)
        else:
            d['pv'], d['vs'] = 99, 0
        vs, qq, cf, bs, core = d['vs'], d['q'], d['cf'], d['bs'], d['core']
        d['total'] = round(0.40 * vs + 0.20 * qq + 0.15 * cf + 0.15 * bs + 0.10 * core, 2)
        d['total1'] = round(0.25 * vs + 0.25 * qq + 0.20 * cf + 0.15 * bs + 0.15 * core, 2)
    h = h[:a] + json.dumps(S, ensure_ascii=False) + h[b:]
    # price timestamp everywhere the report states it
    h = re.sub(r'ราคาปิด 13 พ\.ย\. 2026 \(NVDA ใช้ราคา after-hours 17 พ\.ย\. หลังประกาศงบ\)', f'ราคาปิด หรือราคาล่าสุด ณ {stamp}', h)
    h = re.sub(r'ราคาปิด 13 พ\.ย\. 2026 \(NVDA 17 พ\.ย\.\)', f'ราคาล่าสุด ณ {stamp}', h)
    h = re.sub(r'ราคาปิด 13 พ\.ย\. 2026', f'ราคาล่าสุด ณ {stamp}', h)
    h = re.sub(r'ราคาปิด หรือราคาล่าสุด ณ \d{1,2} [^ ]+ \d{4} \d{2}:\d{2} น\.', f'ราคาปิด หรือราคาล่าสุด ณ {stamp}', h)
    h = re.sub(r'ราคาล่าสุด ณ \d{1,2} [^ ]+ \d{4} \d{2}:\d{2} น\.', f'ราคาล่าสุด ณ {stamp}', h)
    h = re.sub(r'<title>[^<]*</title>', '<title>รายงานรายสัปดาห์ Graham</title>', h, count=1)
    h = re.sub(r'<p class="muted">v9 · 18 พ\.ย\. 2026 \(ข้อ C ใหม่: ดูทั้ง 3 ปีและ 5 ปี\) · ',
               '<p class="muted">รายงานรายสัปดาห์ · มูลค่าและด่านต่างๆ ทบทวนตามงบล่าสุด · ตารางและคะแนนใช้ราคาล่าสุด ส่วนราคาที่อ้างในคำอธิบายบางจุดเป็นราคา ณ วันที่เขียน · ', h, count=1)
    h = h.replace('เช็คสัญญาณอัตโนมัติทุกวันจันทร์ 8:41 น.', 'รายงานรายวัน อ.–ส. 08:30 น. · รายสัปดาห์ จ. 08:30 น.')
    h = h.replace('ทุกวันจันทร์ 8:41 น. (เวลาไทย)', 'ทุกวันจันทร์ 08:30 น. (เวลาไทย)')
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, 'w', encoding='utf-8').write(h)
    print(f'wrote {DST} from {os.path.relpath(src, ROOT)} at {stamp}; no price for: {failed or "none"}')
    for t, d in S.items():
        print(f"{t:6} {d['price']:>9} pv {d['pv']:>5} total {d['total']:>5} total1 {d['total1']:>5} {d.get('asof', '')}")


if __name__ == '__main__':
    main()
