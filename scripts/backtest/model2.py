import csv,json
T=['AAPL','MSFT','GOOGL','AMZN','META','NVDA','TSLA','TSM']
Y=list(range(2016,2026))
AAA={2016:3.51,2017:3.60,2018:4.14,2019:3.01,2020:2.35,2021:2.68,2022:5.10,2023:5.61,2024:4.95,2025:5.13,2026:6.12}
SP={2016:2180.39,2017:2564.62,2018:2730.20,2019:3120.46,2020:3585.15,2021:4682.80,2022:3991.73,2023:4502.88,2024:5870.62,2025:6734.11,2026:7537.78}
NDX={2016:4764.47,2017:6258.36,2018:6890.45,2019:8315.52,2020:11937.84,2021:16189.12,2022:11871.15,2023:15817.18,2024:20394.13,2025:25008.24,2026:27943.74}
# prices 2016..2026 (raw close, split-adjusted)
P={'AAPL':[26.78,42.27,47.85,66.44,119.26,150.00,150.04,188.01,225.00,272.41,356.27],
   'MSFT':[58.87,82.98,106.94,149.97,216.51,336.07,241.73,369.67,415.00,510.18,523.88],
   'GOOGL':[38.90,51.80,53.60,66.70,88.50,149.17,98.72,134.62,172.49,276.41,295.77],
   'AMZN':[37.20,56.30,79.70,87.00,156.40,177.28,98.94,143.20,202.61,234.69,266.66],
   'META':[117.20,177.95,143.85,195.10,276.95,347.56,117.08,332.71,554.08,609.46,641.69],
   'NVDA':[2.30,5.18,4.98,5.24,13.48,29.99,16.67,48.89,141.98,190.17,162.85],
   'TSLA':[12.25,20.70,23.30,23.50,136.20,337.80,194.42,242.84,320.72,404.35,390.22],
   'TSM':[29.80,40.60,37.50,53.20,98.00,118.00,81.00,99.50,188.00,290.00,398.73]}
# normalized TTM EPS 2013..2026 (TSM in TWD/share)
E13={'AAPL':[1.42,1.61,2.31,2.08,2.30,2.98,2.97,3.28,5.61,6.11,6.13,6.75,7.46,8.98],
 'MSFT':[2.65,2.64,2.75,2.88,3.33,4.18,4.99,6.20,8.42,9.29,10.45,12.12,14.47,17.52],
 'GOOGL':[0.91,1.01,1.12,1.34,1.57,2.00,2.35,2.45,4.40,5.03,5.35,7.40,9.20,10.70],
 'AMZN':[0.03,-0.02,0.03,0.20,0.19,0.81,1.13,1.71,2.50,1.06,2.05,4.60,6.45,6.78],
 'META':[0.42,1.00,1.13,3.00,5.90,7.40,8.38,8.78,14.01,10.60,13.40,21.20,28.84,30.74],
 'NVDA':[0.0185,0.021,0.022,0.035,0.088,0.16,0.111,0.136,0.269,0.36,0.42,2.13,3.67,8.30],
 'TSLA':[-0.10,-0.25,-0.40,-0.43,-0.60,-0.71,-0.32,-0.20,0.60,2.76,2.59,1.29,0.70,0.65],
 'TSM':[7.3,9.4,11.6,12.4,13.3,13.4,12.6,17.4,23.93,34.04,33.63,40.52,60.61,95.4]}
FX={2016:31.9,2017:30.2,2018:30.9,2019:30.5,2020:28.6,2021:27.8,2022:31.9,2023:32.2,2024:32.5,2025:31.0,2026:32.9}
# ratios from memory for 2016-2021 (opm, roe, fcf/ni, fcf margin, netdebt/ocf, fcf/ocf)
RM={
'AAPL':{2016:(.28,.36,1.18,.25,-1.0,.80),2017:(.27,.36,1.07,.22,-.8,.79),2018:(.27,.55,1.08,.24,-.4,.82),2019:(.25,.61,1.07,.22,-.2,.84),2020:(.24,.88,1.27,.26,-.1,.91),2021:(.298,1.5,.98,.254,-.5,.89)},
'MSFT':{2016:(.29,.29,1.23,.27,-1.5,.74),2017:(.30,.33,1.2,.29,-1.5,.73),2018:(.33,.38,1.1,.29,-1.0,.71),2019:(.35,.40,.97,.31,-1.0,.69),2020:(.38,.40,.98,.32,-1.0,.70),2021:(.42,.47,.97,.37,-1.0,.70)},
'GOOGL':{2016:(.26,.15,1.2,.28,-3,.70),2017:(.26,.15,1.0,.21,-3,.67),2018:(.23,.18,.75,.17,-2.5,.52),2019:(.21,.17,1.0,.19,-2.5,.64),2020:(.21,.17,1.05,.20,-2.5,.68),2021:(.31,.30,.93,.27,-1.5,.73)},
'AMZN':{2016:(.03,.12,1.2,.06,.2,.55),2017:(.02,.10,1.2,.04,.8,.38),2018:(.04,.22,1.2,.07,.6,.55),2019:(.05,.20,1.2,.07,.8,.55),2020:(.06,.24,.7,.04,.5,.30),2021:(.058,.25,-.07,-.006,.9,-.04)},
'META':{2016:(.43,.20,1.0,.40,-3,.70),2017:(.48,.24,.95,.40,-3,.67),2018:(.45,.26,.87,.28,-3,.55),2019:(.34,.26,1.25,.28,-2,.55),2020:(.38,.23,1.1,.27,-2,.55),2021:(.41,.31,.95,.33,-1.0,.67)},
'NVDA':{2016:(.20,.20,1.2,.20,-1,.88),2017:(.30,.30,1.0,.27,-1.5,.90),2018:(.35,.48,.95,.31,-1.5,.88),2019:(.27,.28,1.1,.31,-1.5,.86),2020:(.27,.25,1.3,.30,-.5,.90),2021:(.32,.29,.97,.28,-1.0,.88)},
'TSLA':{2016:(-.05,-.2,-1,-.05,2.5,-1),2017:(-.08,-.3,-1,-.12,3,-1),2018:(-.02,-.2,-1,-.03,2.5,-.5),2019:(.0,-.1,-1,.01,1.5,.15),2020:(.04,.05,1.0,.05,0,.45),2021:(.096,.14,.9,.07,-.5,.33)},
'TSM':{2016:(.39,.25,.6,.18,-1,.36),2017:(.39,.24,.6,.19,-1,.37),2018:(.38,.22,.7,.20,-1,.40),2019:(.35,.20,.5,.14,-1,.30),2020:(.41,.27,.6,.19,-.6,.33),2021:(.41,.29,.45,.19,-.6,.28)}}
LTINV={'AAPL':{2022:120.8,2023:100.5,2024:91.5,2025:77.7,2026:75.0}}
def q(t):
    r=list(csv.DictReader(open(f'q_{t}.csv')))
    for x in r:
        for k in x:
            if k!='end': x[k]=float(x[k]) if x[k] else None
    return r
def ratios(t,y):
    if y<=2021: return RM[t][y]
    r=q(t); cutoff=f'{y}-08-15' if (t=='NVDA' and y<2026) else (f'{y}-11-01' if y==2026 else f'{y}-10-05')
    w=[x for x in r if x['end']<=cutoff][-4:]; s=lambda k:sum(x[k] for x in w); b=w[-1]
    rev,op,ni,ocf,fcf=s('rev'),s('op'),s('ni'),s('ocf'),s('fcf')
    cash=b['cash']+LTINV.get(t,{}).get(y,0)*1000
    nd=(b['debt']-cash)/ocf if ocf>0 else 3
    return (op/rev, ni/b['eq'], fcf/ni if ni>0 else -1, fcf/rev, nd, fcf/ocf if ocf>0 else -1)
cl=lambda v,a=0,b=10:max(a,min(b,v))
def subs(t,y,pv):
    opm,roe,conv,fm,nd,ret=ratios(t,y)
    return dict(vs=0 if pv is None else cl(10*(2.0-pv)/1.3), q=0.5*cl(opm/.4*10)+0.5*cl(roe/.35*10),
        cf=0.5*cl(conv*10)+0.5*cl(fm/.25*10), bs=10 if nd<=0 else cl(10-2.5*nd), core=cl(ret/.6*10))
W1=dict(vs=.25,q=.25,cf=.20,bs=.15,core=.15)
W2=dict(vs=.40,q=.20,cf=.15,bs=.15,core=.10)
def evaluate(t,y,price=None,v2=True):
    k=y-2013; e=E13[t]; e0,e3=e[k-3],e[k]
    hist=[e[k-2],e[k-1],e[k]]
    cagr=((e3/e0)**(1/3)-1) if (e0>0 and e3>0) else None
    g=(15.0 if e3>0 else None) if cagr is None else cl(0.75*cagr*100,0,15)
    # rule C: skip Graham only if EPS grew >40%/yr over BOTH 3y and 5y (3y only when 5y data is missing), or a loss in 3y
    e5=e[k-5] if k>=5 else None
    cagr5=((e3/e5)**(1/5)-1) if (e5 and e5>0 and e3>0) else None
    fast = cagr is None or (cagr>0.40 and (cagr5 is None or cagr5>0.40))
    flag = v2 and (fast or min(hist)<=0)
    eps=e3/FX[y]*5 if t=='TSM' else e3
    Yld=max(AAA[y],4.4) if v2 else AAA[y]
    price=price if price is not None else P[t][y-2016]
    if eps<=0 or g is None: V=buy=pv=None
    else: V=eps*(8.5+2*g)*4.4/Yld; buy=0.7*V; pv=price/V
    s=subs(t,y,pv); Wt=W2 if v2 else W1; total=sum(s[x]*Wt[x] for x in Wt)
    gate=s['q']>=6 and s['cf']>=5 and s['bs']>=5
    if v2: sig=(pv is not None and pv<=0.70 and gate and not flag)
    else: sig=(pv is not None and pv<=0.70 and total>=7.5)
    return dict(t=t,y=y,price=price,eps=eps,g=g,cagr=cagr,flag=flag,V=V,buy=buy,pv=pv,total=total,gate=gate,sig=sig,Y=Yld,**s)
def fwd(t,y,n):
    i=y-2016
    return None if i+n>10 else P[t][i+n]/P[t][i]-1
def idx(y,n,D): return None if y+n>2026 else D[y+n]/D[y]-1
def run(v2):
    out={}
    for y in Y:
        rows=[]
        for t in T:
            r=evaluate(t,y,v2=v2); r.update(r1=fwd(t,y,1),r3=fwd(t,y,3),rN=fwd(t,y,2026-y)); rows.append(r)
        out[y]=dict(rows=rows,Y=rows[0]['Y'],sp1=idx(y,1,SP),sp3=idx(y,3,SP),spN=idx(y,2026-y,SP),nd1=idx(y,1,NDX),nd3=idx(y,3,NDX),ndN=idx(y,2026-y,NDX))
    return out
def port(o,mode):
    v=[100]
    for y in Y:
        rows=o[y]['rows']; sig=[r for r in rows if r['sig']]
        if mode=='sig': rr=sum(r['r1'] for r in sig)/len(sig) if sig else o[y]['sp1']
        elif mode=='ew': rr=sum(r['r1'] for r in rows)/len(rows)
        elif mode=='sp': rr=o[y]['sp1']
        elif mode=='ndx': rr=o[y]['nd1']
        elif mode=='cheap3':
            c=sorted([r for r in rows if r['pv']],key=lambda r:r['pv'])[:3]; rr=sum(r['r1'] for r in c)/3
        v.append(v[-1]*(1+rr))
    return v
if __name__=='__main__':
    for v2 in (False,True):
        o=run(v2); print('=== v2' if v2 else '=== v1')
        for y in Y:
            print(y,'Y',o[y]['Y'],'sp1 %.0f'%(o[y]['sp1']*100),[ (r['t'],round(r['pv'],2) if r['pv'] else None,round(r['total'],1),'F' if r['flag'] else '','G' if r['gate'] else '','*' if r['sig'] else '') for r in o[y]['rows']])
        for m in ['sig','cheap3','ew','sp','ndx']: v=port(o,m); print(m,[round(x) for x in v],'CAGR %.1f'%(((v[-1]/100)**(1/10)-1)*100))
        sg=[(y,r) for y in Y for r in o[y]['rows'] if r['sig']]
        print('n',len(sg),'1y beat',sum(r['r1']>o[y]['sp1'] for y,r in sg),'3y n',sum(r['r3'] is not None for y,r in sg),'3y beat',sum(r['r3'] is not None and r['r3']>o[y]['sp3'] for y,r in sg),'N beat',sum(r['rN']>o[y]['spN'] for y,r in sg),'3y pos',sum(r['r3'] is not None and r['r3']>0 for y,r in sg))
        for y,r in sg: print('  ',y,r['t'],'1y %.0f/%.0f 3y %s/%s N %.0f/%.0f'%(r['r1']*100,o[y]['sp1']*100, None if r['r3'] is None else round(r['r3']*100), None if o[y]['sp3'] is None else round(o[y]['sp3']*100), r['rN']*100,o[y]['spN']*100))
