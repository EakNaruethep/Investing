#!/usr/bin/env python3
"""Weekly step: refresh output/reports/weekly-report.html with the latest traded prices.

The weekly report keeps the layout of archive/2026-11-24/2026-11-16-graham-mag7-valuation.html.
This script only updates what depends on price: in the S={...} data block it rewrites price,
pv (price / V), vs (valuation score), total (weights 40/20/15/15/10) and total1 (old weights
25/25/20/15/15), and it rewrites the price timestamp in the header. EPS, g, V, the buy price,
the quality gates and rules C and D are not touched here: the weekly review updates them in
the S block when new results, a new Aaa or news arrive, before running this script.

It also refreshes the evidence for the cash-flow claims: the last 5 quarters of operating
cash flow, capex and free cash flow per stock from Yahoo's fundamentals API, written into the
EV={...} block and shown in appendix ค as a table whose rows have id="ev-fcf-<TICKER>". Claims in
the report such as "FCF ติดลบ 2 ไตรมาสล่าสุด" link there with <a class="ev" href="#ev-fcf-GOOGL">.
If the report lacks the evidence table, its CSS or its script, they are added. The script then
checks each FCF claim in the gate text (gw) against the data and prints a warning on a mismatch.

Template: the current weekly-report.html if it has an S block, otherwise the 16 Nov report.
Run from the repo root:  python3 scripts/dashboard/refresh_weekly.py
Evidence only, prices untouched:  python3 scripts/dashboard/refresh_weekly.py --evidence-only
"""
import csv, json, os, re, sys, time, urllib.request
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


EV_TYPES = ['quarterlyOperatingCashFlow', 'quarterlyCapitalExpenditure', 'quarterlyFreeCashFlow']

EV_CSS = """
/* evidence links: a key claim links to the data that backs it */
a.ev{color:#6e9fff;text-decoration:underline dotted;text-underline-offset:3px}
a.ev::after{content:"\\00a0🔎";font-size:11px}
a.ev.ev-missing{color:var(--bad);text-decoration:line-through}
[id]{scroll-margin-top:12px}
tr:target td,.card:target,h3:target{background:var(--warn-bg)!important;transition:background .4s}
.evtbl td{vertical-align:top}.evtbl .q{font-size:11.5px;color:var(--text-muted)}.evtbl .v{font-size:14px;font-weight:600}
.evtbl .v.neg{color:var(--neg)}.evtbl .v.pos{color:var(--pos)}.evtbl .sm{font-size:11.5px;color:var(--text-secondary)}
"""

EV_HTML = """
<h3 id="ev-fcf" style="margin-top:18px">หลักฐาน: กระแสเงินสดรายไตรมาส 5 ไตรมาสล่าสุด (พันล้าน ตามสกุลเงินในงบ)</h3>
<p class="muted">ใช้ตรวจด่านกระแสเงินสด (cf) และทุกข้อความ "FCF ติดลบ" ในรายงาน ลิงก์ที่มี 🔎 จะพามาที่แถวของหุ้นตัวนั้น · FCF = กระแสเงินสดจากการดำเนินงาน (OCF) − รายจ่ายลงทุน (capex) · ที่มา: Yahoo Finance งบไตรมาสตามที่บริษัทรายงาน ดึงเมื่อ <span id="evasof"></span> · <a href="#status">↑ กลับไปสถานะสัญญาณ</a></p>
<div class="card tblwrap"><table id="evtbl" class="evtbl"></table></div>
"""

EV_JS = """<script>
// evidence: quarterly cash flow (data written by refresh_weekly.py)
const EV={};
(()=>{const TM=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
const ql=s=>{const [y,m]=s.split('-');return TM[+m-1]+' '+y.slice(2)};
const g=v=>v==null?'—':(v<0?'−':'')+Math.abs(v).toFixed(1);
if($('evasof'))$('evasof').textContent=EV.asof||'—';
let h='<tr><th>หุ้น</th><th>ไตรมาสล่าสุด</th>'+[1,2,3,4].map(k=>`<th>ย้อนหลัง ${k}</th>`).join('')+'<th>FCF 4 ไตรมาส</th><th style="text-align:left">ข้อสรุปจากข้อมูล</th></tr>';
for(const t of T){const e=(EV.t||{})[t];h+=`<tr id="ev-fcf-${t}"><td><b>${t}</b><br><span class="muted">${e?e.cur:''}</span></td>`;
if(!e||!e.q.length){h+=`<td colspan="7" class="muted" style="text-align:left">ไม่มีข้อมูลรายไตรมาสจาก Yahoo</td></tr>`;continue}
const q=e.q.slice(-5);
for(const [d,o,c,fc,src] of [...q].reverse())h+=`<td><div class="q">${ql(d)}${src?' *':''}</div><div class="v ${fc<0?'neg':'pos'}">${g(fc)}</div><div class="sm">OCF ${g(o)} · capex ${g(c)}</div></td>`;
const last4=q.slice(-4).reduce((a,r)=>a+r[3],0);let k=0;for(let i=q.length-1;i>=0&&q[i][3]<0;i--)k++;const anyneg=q.filter(r=>r[3]<0).length;
const msg=k?`<b style="color:var(--neg)">FCF ติดลบ ${k} ไตรมาสล่าสุดติดกัน</b>`:anyneg?`FCF ไตรมาสล่าสุดเป็นบวก แต่ติดลบ ${anyneg} ใน ${q.length} ไตรมาส`:'FCF เป็นบวกทุกไตรมาส';
for(let i=0;i<5-q.length;i++)h+='<td></td>';
h+=`<td class="v ${last4<0?'neg':''}">${g(last4)}</td><td style="text-align:left;white-space:normal;min-width:180px">${msg}</td></tr>`}
if($('evtbl'))$('evtbl').innerHTML=h+'<tr><td colspan="8" class="muted" style="text-align:left;white-space:normal">* ไตรมาสที่ Yahoo ไม่มีข้อมูล ใช้ตัวเลขจากงบไตรมาสในไฟล์ scripts/backtest/q_&lt;หุ้น&gt;.csv ของ repo แทน</td></tr>';
// every evidence link must land somewhere; flag the ones that do not
document.querySelectorAll('a.ev').forEach(a=>{const id=(a.getAttribute('href')||'').slice(1);if(!id||!document.getElementById(id)){a.classList.add('ev-missing');a.title='ไม่พบหลักฐาน: #'+id;console.warn('evidence link without target',id)}})})();
</script>
"""


def fetch_cf(sym):
    """Last quarters of OCF, capex and FCF (bn, reporting currency) from Yahoo's fundamentals API."""
    now = int(time.time())
    url = ('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'
           f'{sym}?type={",".join(EV_TYPES)}&period1={now - 3 * 366 * 86400}&period2={now}')
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.load(r)['timeseries']['result']
            rows, cur = {}, ''
            for x in res:
                typ = x['meta']['type'][0]
                for v in x.get(typ) or []:
                    if v and v.get('reportedValue'):
                        rows.setdefault(v['asOfDate'], {})[typ] = v['reportedValue']['raw'] / 1e9
                        cur = v.get('currencyCode') or cur
            q = []
            for d in sorted(rows):
                o, c, f = (rows[d].get(k) for k in EV_TYPES)
                if f is None and o is not None and c is not None:
                    f = o + c
                if f is None:
                    continue
                q.append([d, None if o is None else round(o, 2), None if c is None else round(-c, 2), round(f, 2)])
            # Yahoo sometimes skips a quarter (e.g. AMZN Jun 2026). Fill such gaps from the repo's
            # quarterly file scripts/backtest/q_<TICKER>.csv (USD millions) and mark them 'repo'.
            have = {r[0] for r in q}
            days = lambda x: datetime.strptime(x[:10], '%Y-%m-%d').toordinal()
            csvp = os.path.join(ROOT, 'scripts', 'backtest', f'q_{sym}.csv')
            if q and cur == 'USD' and os.path.exists(csvp):
                for row in csv.DictReader(open(csvp, encoding='utf-8-sig')):
                    row = {k.strip().lower(): v for k, v in row.items()}
                    d = row.get('end', '')
                    if q[0][0] < d < q[-1][0] and row.get('fcf') and not any(abs(days(d) - days(x)) < 45 for x in have):
                        q.append([d, round(float(row['ocf']) / 1e3, 2), round(-float(row['capex']) / 1e3, 2),
                                  round(float(row['fcf']) / 1e3, 2), 'repo'])
                q.sort(key=lambda r: r[0])
            return {'cur': cur, 'q': q[-5:]}
        except Exception as e:
            print(f'cash-flow fetch {sym} attempt {attempt + 1}: {e!r}')
            time.sleep(2 * (attempt + 1))
    return None


def neg_streak(q):
    k = 0
    for r in reversed(q):
        if r[3] >= 0:
            break
        k += 1
    return k


def add_evidence(h, S, stamp):
    """Insert the evidence table/CSS/script if missing, refresh EV={...}, check FCF claims."""
    if 'a.ev{' not in h:
        h = h.replace('</style>', EV_CSS + '</style>', 1)
    if 'id="ev-fcf"' not in h:
        m = re.search(r'<div class="mini" id="c2"></div>\n', h)
        if not m:
            sys.exit('No cash-flow chart (id="c2") to put the evidence table after')
        h = h[:m.end()] + EV_HTML + h[m.end():]
    # the evidence script is owned by this file: drop any older copy and add the current one
    h = re.sub(r'<script>\n// evidence: quarterly cash flow.*?</script>\n', '', h, flags=re.S)
    h = h.replace('</body>', EV_JS + '</body>', 1)
    ev = {'asof': stamp, 't': {}}
    for t in S:
        r = fetch_cf(t)
        if r and r['q']:
            ev['t'][t] = r
    h = re.sub(r'const EV=\{.*?\};\n', lambda _: 'const EV=' + json.dumps(ev, ensure_ascii=False) + ';\n', h, count=1)
    warn = []
    for t, d in S.items():
        gw, e = d.get('gw', ''), ev['t'].get(t)
        if 'FCF' not in gw or 'ติดลบ' not in gw:
            continue
        if not e:
            warn.append(f'{t}: "{gw}" but no quarterly data to back it')
            continue
        k = neg_streak(e['q'])
        n = re.search(r'ติดลบ (\d+) ไตรมาส', gw)
        if k == 0 and ('ล่าสุด' in gw or n):
            warn.append(f'{t}: "{gw}" but latest quarter FCF is {e["q"][-1][3]:+.1f}')
        elif n and int(n.group(1)) != k:
            warn.append(f'{t}: "{gw}" but data shows {k} negative quarter(s) in a row')
    for t, e in ev['t'].items():
        print(f"EV {t:6} {e['cur']} FCF " + ' '.join(f"{r[0][:7]}:{r[3]:+.1f}" for r in e['q']) + f"  neg streak {neg_streak(e['q'])}")
    for w in warn:
        print('WARNING claim vs data:', w)
    return h


def main():
    src = DST if os.path.exists(DST) and 'S={' in open(DST, encoding='utf-8').read() else BASE
    h = open(src, encoding='utf-8').read()
    a, b, S = s_block(h)
    if S is None:
        sys.exit(f'No S={{...}} block in {src}')
    now = datetime.now(ICT)
    stamp = f'{now.day} {TH_MON[now.month - 1]} {now.year} {now:%H:%M} น.'
    failed = []
    evidence_only = '--evidence-only' in sys.argv
    for t, d in ({} if evidence_only else S).items():
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
    h = add_evidence(h, S, stamp)
    if evidence_only:
        open(DST, 'w', encoding='utf-8').write(h)
        print(f'wrote evidence only to {DST} at {stamp}')
        return
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
