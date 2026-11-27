#!/usr/bin/env python3
"""Buy-signal alert: notify Eak when a stock passes the buy rules (tier 1 or tier 2).

Uses the same rule-A check as the daily report (price_watch.evaluate: latest regular-session
price from Yahoo against the buy prices in data/watchlist.json, with the rule B/C/D results
from the weekly review). It writes no files.

Notification = a GitHub issue labelled "buy-signal" in this repo. GitHub sends the repo owner
an email and a push to the GitHub mobile app. One open issue per stock, so a signal that lasts
for days notifies once:
  - stock enters tier 1/2      -> open an issue
  - tier changes (2 -> 1 ...)  -> comment on its issue
  - signal gone                -> comment and close the issue
If NTFY_TOPIC is set, the same text also goes to https://ntfy.sh/<topic> (optional phone push).

Run in GitHub Actions (.github/workflows/buy-signal-alert.yml) with GITHUB_TOKEN and
GITHUB_REPOSITORY set.  Locally:  python3 scripts/dashboard/signal_alert.py --dry-run
Standard library only.
"""
import json, os, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from price_watch import evaluate, load_watchlist, fmt, pc  # noqa: E402

LABEL = 'buy-signal'
TIER = dict(t1='ระดับ 1 · ซื้อเต็ม', t2='ระดับ 2 · ทยอยซื้อ 1/3')
REPORT = 'https://eaknaruethep.github.io/Investing/output/reports/daily-report.html'


def gh(method, path, body=None):
    url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': f"Bearer {os.environ['GITHUB_TOKEN']}",
                                          'Accept': 'application/vnd.github+json', 'User-Agent': 'buy-signal-alert'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r) if r.status != 204 else None


def ntfy(title, msg):
    topic = os.environ.get('NTFY_TOPIC')
    if not topic:
        return
    try:
        req = urllib.request.Request(f'https://ntfy.sh/{topic}', data=msg.encode('utf-8'), method='POST',
                                     headers={'Title': title.encode('utf-8').decode('latin-1', 'ignore') or 'Buy signal',
                                              'Tags': 'bell', 'Click': REPORT, 'Priority': 'high'})
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:  # the GitHub issue is the main channel; ntfy is best-effort
        print('ntfy failed:', e)


def title_of(r):
    return f"สัญญาณซื้อ {r['t']} · {TIER[r['status']]}"


def body_of(r, W):
    return (f"**{r['t']} ({r['name']})** ผ่านเกณฑ์ซื้อ **{TIER[r['status']]}**\n\n"
            f"| | |\n|---|---|\n"
            f"| ราคา ({r['sess']} {r['when']} เวลาไทย) | {fmt(r['price'])} |\n"
            f"| ราคาซื้อ (0.7V) | {fmt(r['buy'])} |\n"
            f"| ราคา/มูลค่า | {fmt(r['pv'])}× |\n"
            f"| เหตุผล | {r['why']} |\n\n"
            f"ตัดสินด้วยราคาในเวลาทำการ (ไม่ใช้ราคาก่อนเปิด/หลังปิดตลาด) · ราคาซื้อจากรายงานรายสัปดาห์ {W['builtAt']}\n\n"
            f"ก่อนซื้อ: ตรวจข่าวล่าสุด (ข้อ D) · รายงาน: {REPORT}\n\n_ไม่ใช่คำแนะนำการลงทุน_")


def main():
    dry = '--dry-run' in sys.argv
    W = load_watchlist()
    if '--test' in sys.argv:
        rows = [dict(t='TEST', name='ทดสอบการแจ้งเตือน', status='t1', price=1.0, buy=1.0, pv=0.7,
                     sess='ทดสอบ', when='', why='ข้อความทดสอบ ไม่ใช่สัญญาณจริง')]
    else:
        rows = evaluate(W)
    sig = {r['t']: r for r in rows if r['status'] in TIER}
    priced = {r['t'] for r in rows if r.get('price')}
    for r in rows:
        print(f"{r['t']:<5} {fmt(r['price']):>9} {r['status']:<8} {r['why']}")
    if not priced:
        sys.exit('Yahoo returned no prices; no alerts changed.')
    if dry:
        print('dry run; signals:', ', '.join(f"{t} {r['status']}" for t, r in sig.items()) or 'none')
        return

    try:
        gh('POST', '/labels', dict(name=LABEL, color='2ea043', description='Stock passed the buy rules'))
    except urllib.error.HTTPError as e:
        if e.code != 422:  # 422 = label already exists
            raise
    open_issues = {}
    for i in gh('GET', f'/issues?labels={LABEL}&state=open&per_page=100'):
        t = i['title'].split(' · ')[0].replace('สัญญาณซื้อ ', '').strip()
        open_issues[t] = i

    for t, r in sig.items():
        i = open_issues.get(t)
        if i is None:
            n = gh('POST', '/issues', dict(title=title_of(r), body=body_of(r, W), labels=[LABEL]))['number']
            print(f'opened #{n} for {t}')
            ntfy(f'Buy signal {t}', f"{t} {TIER[r['status']]} · ราคา {fmt(r['price'])} ≤ ราคาซื้อ {fmt(r['buy'])}")
        elif i['title'] != title_of(r):
            gh('PATCH', f"/issues/{i['number']}", dict(title=title_of(r)))
            gh('POST', f"/issues/{i['number']}/comments", dict(body='เปลี่ยนระดับ\n\n' + body_of(r, W)))
            print(f"tier changed #{i['number']} for {t}")
            ntfy(f'Buy signal {t}', f"{t} เปลี่ยนเป็น {TIER[r['status']]} · ราคา {fmt(r['price'])}")

    for t, i in open_issues.items():
        if t in sig or (t not in priced and t != 'TEST'):
            continue  # still a signal, or no price this run (don't close on a fetch failure)
        r = next((x for x in rows if x['t'] == t), None)
        note = (f"ราคา {fmt(r['price'])} ({r['sess']} {r['when']}) · สถานะตอนนี้: {r['status']} · {r['why']}"
                if r else 'ไม่อยู่ในรายการหุ้นแล้ว')
        gh('POST', f"/issues/{i['number']}/comments", dict(body='หลุดเกณฑ์ซื้อแล้ว · ' + note))
        gh('PATCH', f"/issues/{i['number']}", dict(state='closed', state_reason='completed'))
        print(f"closed #{i['number']} for {t}")


if __name__ == '__main__':
    main()
