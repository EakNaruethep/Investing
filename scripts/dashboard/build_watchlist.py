#!/usr/bin/env python3
"""Weekly step: copy each stock's value, buy price and gate results out of the weekly report
(its JavaScript data object "S={...}") into data/watchlist.json, which the daily report reads.
Run from the repo root:  python3 scripts/dashboard/build_watchlist.py [path/to/weekly-report.html]
"""
import json, os, re, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
YAHOO = {'SPCX': None}   # SpaceX: no Yahoo quote yet -> the daily report skips it


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'output', 'reports', 'weekly-report.html')
    h = open(path, encoding='utf-8').read()
    i = h.find('S={')
    if i < 0:
        sys.exit(f'No S={{...}} data block in {path}; the weekly report must keep it.')
    i += 2
    depth = 0
    for k in range(i, len(h)):
        if h[k] == '{':
            depth += 1
        elif h[k] == '}':
            depth -= 1
            if depth == 0:
                break
    S = json.loads(h[i:k + 1])
    m = re.search(r'Aaa ต\.ค\. \d{4} = ([\d.]+)%', h) or re.search(r'Aaa[^0-9]{0,40}([\d.]+)%', h)
    aaa = float(m.group(1))
    m = re.search(r'ราคาปิด ([^·<]+)', h)
    hp = os.path.join(ROOT, 'data', 'd_holds.json')
    holds = json.load(open(hp, encoding='utf-8-sig')) if os.path.exists(hp) else {}
    stocks = []
    for t, x in S.items():
        stocks.append(dict(t=t, yahoo=YAHOO.get(t, t), name=x.get('name'), V=x.get('V'), buy=x.get('buy'),
                           eps=x.get('eps'), g=x.get('g'), na=bool(x.get('na')), gate=bool(x.get('gate')),
                           gateNote=x.get('gw', ''), flag=bool(x.get('flag')), flagNote=x.get('fw', ''),
                           score1=x.get('total1'), vs=x.get('vs'), q=x.get('q'), cf=x.get('cf'), bs=x.get('bs'),
                           hold=holds.get(t, ''), reportPrice=x.get('price')))
    out = dict(builtAt=datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M'),
               reportAsOf=m.group(1).strip() if m else '', aaa=aaa, yld=max(aaa, 4.4),
               report=os.path.basename(path), stocks=stocks)
    dst = os.path.join(ROOT, 'data', 'watchlist.json')
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'wrote {dst} ({len(stocks)} stocks, Aaa {aaa}%)')


if __name__ == '__main__':
    main()
