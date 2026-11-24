from model2 import *
import json, statistics as st
o1 = run(False); o2 = run(True)
TW = 1/3  # tier-2 position size relative to a full position

def basket(y, ruleC_t2=True):
    rows2 = {r['t']: r for r in o2[y]['rows']}
    rows1 = {r['t']: r for r in o1[y]['rows']}
    t1 = [t for t in T if rows2[t]['sig']]
    t2 = [t for t in T if t not in t1 and rows1[t]['sig'] and (not ruleC_t2 or not rows2[t]['flag'])]
    w = {t: 1.0 for t in t1}; w.update({t: TW for t in t2})
    s = sum(w.values())
    if s >= 1: w = {t: v/s for t, v in w.items()}; cash = 0.0
    else: cash = 1 - s  # remainder stays in S&P 500 (IVV)
    return t1, t2, w, cash

def ret(y, n, w, cash):
    sp = idx(y, n, SP)
    if sp is None: return None
    return sum(v*fwd(t, y, n) for t, v in w.items()) + cash*sp

def curve(ruleC_t2=True):
    v = [100]
    for y in Y:
        t1, t2, w, cash = basket(y, ruleC_t2)
        v.append(v[-1]*(1+ret(y, 1, w, cash)))
    return v

years = []
for y in Y:
    t1, t2, w, cash = basket(y)
    rows2 = {r['t']: r for r in o2[y]['rows']}
    rows1 = {r['t']: r for r in o1[y]['rows']}
    # stocks blocked only by rule C (would have been tier 2 under old rule)
    blockedC = [t for t in T if rows1[t]['sig'] and rows2[t]['flag'] and not rows2[t]['sig']]
    years.append(dict(y=y, aaa=AAA[y], Y=max(AAA[y], 4.4), t1=t1, t2=t2, blockedC=blockedC, w=w, cash=cash,
        r1=ret(y, 1, w, cash), sp1=idx(y, 1, SP), nd1=idx(y, 1, NDX),
        r3=ret(y, 3, w, cash), sp3=idx(y, 3, SP),
        rN=ret(y, 2026-y, w, cash), spN=idx(y, 2026-y, SP),
        rows=[dict(t=t, pv2=rows2[t]['pv'], pv1=rows1[t]['pv'], gate=rows2[t]['gate'], flag=rows2[t]['flag'],
                   cagr=rows2[t]['cagr'], tot1=rows1[t]['total'], q=rows2[t]['q'], cf=rows2[t]['cf'], bs=rows2[t]['bs'],
                   tier=1 if t in t1 else (2 if t in t2 else 0), r1=rows2[t]['r1'], r3=rows2[t]['r3'], rN=rows2[t]['rN']) for t in T]))

sigs = []
for Yr in years:
    for r in Yr['rows']:
        if r['tier']:
            sigs.append(dict(y=Yr['y'], t=r['t'], tier=r['tier'], pv=r['pv2'] if r['tier'] == 1 else r['pv1'],
                             r1=r['r1'], r3=r['r3'], rN=r['rN'], sp1=Yr['sp1'], sp3=Yr['sp3'], spN=Yr['spN']))

def stats(S):
    s3 = [x for x in S if x['r3'] is not None]
    return dict(n=len(S), b1=sum(x['r1'] > x['sp1'] for x in S), neg1=sum(x['r1'] < 0 for x in S),
                n3=len(s3), b3=sum(x['r3'] > x['sp3'] for x in s3), pos3=sum(x['r3'] > 0 for x in s3),
                bN=sum(x['rN'] > x['spN'] for x in S),
                med1=st.median([x['r1']-x['sp1'] for x in S]) if S else None,
                med3=st.median([x['r3']-x['sp3'] for x in s3]) if s3 else None,
                worst1=min(x['r1'] for x in S) if S else None)

res = dict(tier=curve(True), tier_noC=curve(False), sp=port(o2, 'sp'), ndx=port(o2, 'ndx'), ew=port(o2, 'ew'))
cagr = {k: ((v[-1]/100)**(1/10)-1) for k, v in res.items()}
# max drawdown on yearly points
def mdd(v):
    pk = v[0]; m = 0
    for x in v: pk = max(pk, x); m = min(m, x/pk-1)
    return m
dd = {k: mdd(v) for k, v in res.items()}
yrs_beat = sum(Yr['r1'] > Yr['sp1'] for Yr in years)
coh = [Yr for Yr in years if Yr['r3'] is not None]
coh_beat = sum(Yr['r3'] > Yr['sp3'] for Yr in coh)
out = dict(Y=Y, res=res, cagr=cagr, dd=dd, years=years, sigs=sigs,
           st_all=stats(sigs), st1=stats([s for s in sigs if s['tier'] == 1]), st2=stats([s for s in sigs if s['tier'] == 2]),
           yrs_beat=yrs_beat, coh_n=len(coh), coh_beat=coh_beat)
json.dump(out, open('tier.json', 'w'), default=float)
print({k: round(v[-1]) for k, v in res.items()}, {k: round(v*100, 1) for k, v in cagr.items()}, {k: round(v*100) for k, v in dd.items()})
print('all', out['st_all']); print('t1', out['st1']); print('t2', out['st2'])
print('years beat', yrs_beat, '/10 ; 3y cohorts beat', coh_beat, '/', len(coh))
for Yr in years:
    print(Yr['y'], 'Y', Yr['Y'], 'T1', Yr['t1'], 'T2', Yr['t2'], 'C-block', Yr['blockedC'], 'cash %.2f' % Yr['cash'],
          '1y %.0f vs %.0f' % (Yr['r1']*100, Yr['sp1']*100), '3y', None if Yr['r3'] is None else round(Yr['r3']*100), None if Yr['sp3'] is None else round(Yr['sp3']*100))
