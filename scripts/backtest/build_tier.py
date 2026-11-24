import json, re
src = open('../../output/reports/2026-11-16-graham-mag7-valuation.html', encoding='utf-8').read()
css = src[src.index('<style>'):src.index('</style>')+8]
D = json.load(open('tier.json'))
st_all, st1, st2 = D['st_all'], D['st1'], D['st2']
fin = {k: round(v[-1]) for k, v in D['res'].items()}
cg = {k: v*100 for k, v in D['cagr'].items()}
dd = {k: v*100 for k, v in D['dd'].items()}
pct = lambda x: f"{x*100:+.0f}%"

html = f'''<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backtest 10 ปี Graham</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap" rel="stylesheet">
{css}
<style>
.banner{{border-radius:14px;padding:18px 20px;margin-top:16px;border:2px solid var(--good);background:var(--good-bg)}}
.banner .t{{font-size:22px;font-weight:700;line-height:1.3;color:var(--good)}}
.banner p{{color:var(--text-secondary);margin:6px 0 0}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(200px,100%),1fr));gap:12px;margin-top:12px}}
.kpi .card{{margin-top:0}}
.kpi .big{{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}}
.pos{{color:var(--good)}} .neg{{color:var(--bad)}}
.hm td{{text-align:center}} .hm td:first-child{{text-align:left}}
.cell{{display:inline-block;min-width:44px;padding:3px 6px;border-radius:6px;font-size:12.5px;font-weight:600}}
.c1{{background:var(--good);color:var(--bg)}} .c2{{background:var(--good-bg);color:var(--good)}} .cC{{background:var(--warn-bg);color:var(--warn)}} .c0{{color:var(--text-muted);font-weight:400}}
</style>
</head>
<body>
<div class="wrap">
<h1>Backtest กติกา Graham 2 ระดับ (พ.ย. 2016 – พ.ย. 2026)</h1>
<p class="sub">ทดสอบกติกาที่ใช้จริงในรายงานหลัก กับ Apple, Microsoft, Alphabet, Amazon, Meta, Nvidia, Tesla และ TSMC ณ กลาง พ.ย. ของทุกปี</p>
<p class="muted">จัดทำ 18 พ.ย. 2026 · เก็บไว้เป็นหลักฐานของวิธีที่ใช้ · <a href="https://claude.ai/artifact/2FBwxrUSgqUR1jhgjxrCeW">รายงานสัญญาณซื้อปัจจุบัน</a> · <a href="https://claude.ai/artifact/VpAJGvjyxnCMRdnQyx7mgN">backtest 10 ปีที่เทียบ v1/v2</a></p>

<div class="banner"><div class="t">$100 → ${fin['tier']} ใน 10 ปี เทียบ S&amp;P 500 ${fin['sp']} และ Nasdaq-100 ${fin['ndx']}</div>
<p>โตเฉลี่ย {cg['tier']:.1f}%/ปี เทียบ S&amp;P 500 {cg['sp']:.1f}%/ปี · สัญญาณที่ถือครบ 3 ปีชนะ S&amp;P 500 {st_all['b3']}/{st_all['n3']} ครั้ง และไม่มีครั้งไหนขาดทุนเมื่อถือครบ 3 ปี ({st_all['pos3']}/{st_all['n3']} เป็นบวก) · แต่ปีแรกแพ้ได้หนัก: ปี 2021 ลง {D['years'][5]['r1']*100:.0f}% · drawdown สูงสุด {dd['tier']:.0f}% (S&amp;P {dd['sp']:.0f}%)</p></div>

<div class="kpi">
<div class="card"><div class="muted">มูลค่าสุดท้าย ($100 เริ่ม พ.ย. 2016)</div><div class="big">${fin['tier']}</div><div class="muted">S&amp;P ${fin['sp']} · NDX ${fin['ndx']}</div></div>
<div class="card"><div class="muted">ระดับ 1: ชนะ S&amp;P เมื่อถือ 3 ปี</div><div class="big">{st1['b3']}/{st1['n3']}</div><div class="muted">ส่วนต่างมัธยฐาน {pct(st1['med3'])} ใน 3 ปี</div></div>
<div class="card"><div class="muted">ระดับ 2: ชนะ S&amp;P เมื่อถือ 3 ปี</div><div class="big">{st2['b3']}/{st2['n3']}</div><div class="muted">ส่วนต่างมัธยฐาน {pct(st2['med3'])} ใน 3 ปี</div></div>
<div class="card"><div class="muted">ปีที่มีสัญญาณ แล้วชนะ S&amp;P ใน 1 ปี</div><div class="big">5/8</div><div class="muted">2023–2024 ไม่มีสัญญาณ เงินอยู่ใน S&amp;P</div></div>
</div>

<h2>1. กติกาที่ทดสอบ และวิธีจำลอง</h2>
<div class="card">
<div class="tblwrap"><table>
<tr><th>ข้อ</th><th style="text-align:left">ระดับ 1: ซื้อเต็ม</th><th style="text-align:left">ระดับ 2: ทยอย 1/3</th></tr>
<tr><td>A. ราคา</td><td style="text-align:left;white-space:normal">P/V ≤ 0.70 โดย Y = max(Aaa, 4.4%)</td><td style="text-align:left;white-space:normal">P/V ≤ 0.70 โดยใช้ Aaa จริง</td></tr>
<tr><td>B. คุณภาพ</td><td style="text-align:left;white-space:normal">ผ่านด่าน q ≥ 6, cf ≥ 5, bs ≥ 5</td><td style="text-align:left;white-space:normal">คะแนนน้ำหนักเดิม (25/25/20/15/15) ≥ 7.5</td></tr>
<tr><td>C. ใช้สูตรได้</td><td style="text-align:left;white-space:normal" colspan="2">EPS ไม่ได้โตเกิน 40%/ปี ทั้งเฉลี่ย 3 ปีและ 5 ปี และไม่ขาดทุนใน 3 ปี (ใช้กับทั้ง 2 ระดับ · ปี 2016–2017 ไม่มีข้อมูล 5 ปี ใช้ 3 ปีอย่างเดียว)</td></tr>
<tr><td>D. ข่าวสำคัญ</td><td style="text-align:left;white-space:normal" colspan="2"><b>ทดสอบไม่ได้</b> (ต้องใช้วิจารณญาณกับข่าว ณ เวลานั้น) จึงไม่ได้ใช้ในการจำลอง</td></tr>
<tr><td>ไม่มีสัญญาณ</td><td style="text-align:left;white-space:normal" colspan="2">เงินอยู่ใน S&amp;P 500 (เทียบ IVV)</td></tr>
</table></div>
<p style="margin-top:10px"><b>วิธีจำลองพอร์ต:</b> ทุกกลาง พ.ย. ตรวจสัญญาณใหม่ หุ้นระดับ 1 ได้น้ำหนัก 1 ส่วน หุ้นระดับ 2 ได้ 1/3 ส่วน ถ้ารวมกันไม่ถึง 1 ส่วน ส่วนที่เหลืออยู่ใน S&amp;P 500 ถ้าเกิน 1 ส่วน แบ่งตามสัดส่วน ถือ 1 ปีแล้วจัดใหม่ · ผลต่อสัญญาณดูทั้ง 1 ปี, 3 ปี (ระยะที่กติกาตั้งใจถือ) และถือถึง พ.ย. 2026</p>
<p class="muted">g = 0.75 × EPS CAGR 3 ปีย้อนหลัง (สูงสุด 15%) เพราะไม่มีคาดการณ์นักวิเคราะห์ในอดีต · คะแนนเป็นแบบกฎจากงบ (op margin, ROE, FCF/กำไร, FCF margin, หนี้สุทธิ/OCF, FCF/OCF) เพื่อตัด hindsight · กฎขาย (ไม่ผ่านด่าน 2 ไตรมาสติด) ไม่ได้จำลอง</p>
</div>

<h2>2. มูลค่าพอร์ต $100 ตามเวลา</h2>
<div class="legend"><span><i style="background:var(--s1)"></i>กติกา 2 ระดับ</span><span><i style="background:var(--s4)"></i>Nasdaq-100</span><span><i style="background:var(--text-muted)"></i>S&amp;P 500</span></div>
<div class="card chart"><svg id="c1"></svg></div>
<div class="card tblwrap"><table id="ytbl"></table></div>

<h2>3. สัญญาณแต่ละปี (หุ้น × ปี)</h2>
<p class="sub">ช่องเข้ม = ระดับ 1 · ช่องอ่อน = ระดับ 2 · สีส้ม = ราคาถึงและคะแนนผ่าน แต่ถูกข้อ C กันไว้ · ตัวเลขในช่อง = ผลตอบแทน 3 ปีของหุ้นนั้น (ถ้ามีสัญญาณ)</p>
<div class="card tblwrap"><table class="hm" id="hm"></table></div>

<h2>4. ผลของแต่ละสัญญาณ ({st_all['n']} ครั้ง)</h2>
<div class="card tblwrap"><table id="stbl"></table></div>
<div class="card tblwrap"><table>
<tr><th>สรุป</th><th>จำนวน</th><th>ชนะ S&amp;P 1 ปี</th><th>ติดลบปีแรก</th><th>ชนะ S&amp;P 3 ปี</th><th>ส่วนต่างมัธยฐาน 3 ปี</th><th>แย่สุดปีแรก</th></tr>
<tr><td><b>ระดับ 1</b></td><td>{st1['n']}</td><td>{st1['b1']}/{st1['n']}</td><td>{st1['neg1']}</td><td><b>{st1['b3']}/{st1['n3']}</b></td><td>{pct(st1['med3'])}</td><td>{pct(st1['worst1'])}</td></tr>
<tr><td><b>ระดับ 2</b></td><td>{st2['n']}</td><td>{st2['b1']}/{st2['n']}</td><td>{st2['neg1']}</td><td><b>{st2['b3']}/{st2['n3']}</b></td><td>{pct(st2['med3'])}</td><td>{pct(st2['worst1'])}</td></tr>
<tr><td><b>รวม</b></td><td>{st_all['n']}</td><td>{st_all['b1']}/{st_all['n']}</td><td>{st_all['neg1']}</td><td><b>{st_all['b3']}/{st_all['n3']}</b></td><td>{pct(st_all['med3'])}</td><td>{pct(st_all['worst1'])}</td></tr>
</table></div>

<h2>5. ควรคิดยังไงจากผลนี้</h2>
<div class="card"><ul>
<li><b>ระดับ 1 คือสัญญาณที่น่าเชื่อที่สุด:</b> ถือ 3 ปีชนะ S&amp;P ทุกครั้ง ({st1['b3']}/{st1['n3']}) ส่วนต่างมัธยฐาน {pct(st1['med3'])} จึงสมควรได้เงินเต็มจำนวน</li>
<li><b>ระดับ 2 ช่วยได้ แต่อ่อนกว่า:</b> ชนะ {st2['b3']}/{st2['n3']} ส่วนต่างมัธยฐาน {pct(st2['med3'])} การซื้อแค่ 1/3 จึงเหมาะ ครั้งที่แพ้ (2020 META, 2021 MSFT/GOOGL) ยังเป็นบวกใน 3 ปี แค่น้อยกว่าตลาด</li>
<li><b>ปีแรกเจ็บได้:</b> สัญญาณ พ.ย. 2021 มี 5 ตัว พอร์ตลง {D['years'][5]['r1']*100:.0f}% ในปีแรก (ดอกเบี้ยพุ่ง) แต่ถือ 3 ปีกลับมาชนะ S&amp;P ทุกตัวยกเว้น MSFT/GOOGL จึงต้องตั้งใจถือ 3 ปีจริง และทยอยซื้อได้</li>
<li><b>ข้อ C แทบไม่เสียโอกาส:</b> ถ้าไม่ใช้ข้อ C กับระดับ 2 ได้ ${fin['tier_noC']} แทน ${fin['tier']} (ต่างกันนิดเดียว) แต่ข้อ C ช่วยกันกรณีกำไรพุ่งชั่วคราวแบบ Nvidia ที่สูตร Graham ประเมินเกินจริง</li>
<li><b>ปีที่ไม่มีสัญญาณ ไม่ต้องฝืน:</b> 2023–2024 ไม่มีตัวไหนผ่าน เงินอยู่ใน S&amp;P แล้วได้เท่าตลาด ซึ่งดีกว่าซื้อของแพง</li>
<li><b>ไม่ได้ชนะทุกอย่าง:</b> ซื้อทั้ง 8 ตัวเท่ากันทุกปีได้ ${fin['ew']} แต่ผลนี้มี survivorship bias สูง (เลือกหุ้นที่รู้ว่าชนะมาแล้ว) จึงไม่ใช่เกณฑ์ที่เทียบได้ตรง · กติกาไม่เคยซื้อ Nvidia เลย</li>
</ul></div>

<h2>6. ข้อจำกัด</h2>
<div class="card"><ul>
<li>หุ้นที่ทดสอบคือหุ้นที่ทุกวันนี้รู้แล้วว่าชนะ (survivorship bias) ผลจริงในอนาคตน่าจะต่ำกว่านี้</li>
<li>กติกาถูกปรับหลังเห็นผล backtest 5 ปีแรก มีความเสี่ยง overfitting · ผลปี 2016–2020 ไม่ได้ใช้ตอนออกแบบ v2 จึงพอใช้เป็นการทดสอบนอกตัวอย่างได้บางส่วน</li>
<li>EPS และอัตราส่วนการเงินก่อนปี 2022 และราคาหุ้นหลายจุด มาจากความจำของ Claude ไม่ได้ดึงจากแหล่งข้อมูลทุกตัว อาจคลาดเคลื่อนเล็กน้อย</li>
<li>ไม่รวมปันผล ภาษี ค่าธรรมเนียม และค่าเงินบาท · ข้อ D และกฎขายไม่ได้จำลอง</li>
<li>สัญญาณ พ.ย. 2025 (META) ยังถือไม่ครบ 3 ปี</li>
</ul></div>
<p class="muted">Claude ไม่ใช่ที่ปรึกษาการลงทุนที่ได้รับใบอนุญาต ผลในอดีตไม่รับประกันอนาคต</p>
</div>
<div id="tip"></div>
<script>
const D={json.dumps(D, ensure_ascii=False)};
const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
function el(t,a,p,x){{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(x!=null)e.textContent=x;if(p)p.appendChild(e);return e}}
const tip=$('tip');function bindTip(e,h){{e.addEventListener('mousemove',ev=>{{tip.innerHTML=h;tip.style.opacity=1;tip.style.left=Math.min(ev.clientX+14,innerWidth-270)+'px';tip.style.top=(ev.clientY+14)+'px'}});e.addEventListener('mouseleave',()=>tip.style.opacity=0)}}
const P=v=>v==null?'—':(v>=0?'+':'')+(v*100).toFixed(0)+'%';
const cls=v=>v==null?'':(v>=0?'pos':'neg');
// equity curve (log scale)
(()=>{{const svg=$('c1'),W=900,H=360,L=56,R=70,T0=16,B=34;svg.setAttribute('viewBox',`0 0 ${{W}} ${{H}}`);
const xs=[...D.Y,2026],x=i=>L+i/(xs.length-1)*(W-L-R);const lo=Math.log(80),hi=Math.log(1000),y=v=>T0+(hi-Math.log(v))/(hi-lo)*(H-T0-B);
for(const g of [100,200,400,800]){{el('line',{{x1:L,x2:W-R,y1:y(g),y2:y(g),stroke:'var(--grid)'}},svg);el('text',{{x:L-8,y:y(g)+4,'text-anchor':'end','font-size':12,fill:'var(--text-muted)'}},svg,'$'+g)}}
xs.forEach((yr,i)=>{{if(i%2==0||i==xs.length-1)el('text',{{x:x(i),y:H-10,'text-anchor':'middle','font-size':12,fill:'var(--text-muted)'}},svg,yr)}});
const S=[['sp','S&P 500','var(--text-muted)',2],['ndx','Nasdaq-100','var(--s4)',2],['tier','กติกา 2 ระดับ','var(--s1)',3.5]];
for(const [k,l,c,w] of S){{const v=D.res[k];el('path',{{d:v.map((a,i)=>(i?'L':'M')+x(i)+' '+y(a)).join(''),fill:'none',stroke:c,'stroke-width':w,'stroke-linejoin':'round'}},svg);
el('text',{{x:x(v.length-1)+6,y:y(v[v.length-1])+4,'font-size':13,'font-weight':600,fill:c}},svg,'$'+Math.round(v[v.length-1]));
v.forEach((a,i)=>{{const d=el('circle',{{cx:x(i),cy:y(a),r:k=='tier'?4:2.5,fill:c}},svg);bindTip(d,`<b>${{l}}</b> พ.ย. ${{xs[i]}}<br>$${{Math.round(a)}}`)}})}}
el('text',{{x:L,y:T0-4,'font-size':11,fill:'var(--text-muted)'}},svg,'สเกล log');}})();
// yearly table
(()=>{{let h='<tr><th>ปี (พ.ย.)</th><th>Y ที่ใช้</th><th style="text-align:left">ระดับ 1</th><th style="text-align:left">ระดับ 2</th><th>อยู่ใน S&amp;P</th><th>พอร์ต 1 ปี</th><th>S&amp;P 1 ปี</th><th>ถือ 3 ปี</th><th>S&amp;P 3 ปี</th><th>มูลค่าพอร์ต</th></tr>';
D.years.forEach((r,i)=>{{h+=`<tr><td><b>${{r.y}}</b></td><td>${{r.Y.toFixed(2)}}%</td><td style="text-align:left">${{r.t1.join(', ')||'—'}}</td><td style="text-align:left">${{r.t2.join(', ')||'—'}}</td><td>${{(r.cash*100).toFixed(0)}}%</td><td class="${{cls(r.r1)}}"><b>${{P(r.r1)}}</b></td><td>${{P(r.sp1)}}</td><td class="${{cls(r.r3)}}">${{P(r.r3)}}</td><td>${{P(r.sp3)}}</td><td>$${{Math.round(D.res.tier[i+1])}}</td></tr>`}});
$('ytbl').innerHTML=h+'<tr><td colspan="10" class="muted" style="text-align:left;white-space:normal">"ถือ 3 ปี" = ถ้าซื้อตะกร้าของปีนั้นแล้วถือ 3 ปีโดยไม่ปรับ · 2024–2025 ยังไม่ครบ 3 ปี · Y = max(Aaa, 4.4%) ใช้กับระดับ 1 ส่วนระดับ 2 ใช้ Aaa จริง (ปี 2016–2021 Aaa ต่ำกว่า 4.4%)</td></tr>'}})();
// heatmap
(()=>{{const T=D.years[0].rows.map(r=>r.t);let h='<tr><th>หุ้น</th>'+D.years.map(r=>`<th>${{r.y}}</th>`).join('')+'</tr>';
for(const t of T){{h+=`<tr><td><b>${{t}}</b></td>`;for(const Y of D.years){{const r=Y.rows.find(x=>x.t==t);let c,txt;
if(r.tier==1){{c='c1';txt=P(r.r3)}}else if(r.tier==2){{c='c2';txt=P(r.r3)}}else if(Y.blockedC.includes(t)){{c='cC';txt='C'}}else{{c='c0';txt=r.pv2==null?'ขาดทุน':r.pv2.toFixed(2)+'×'}}
if(txt=='—')txt='ถือไม่ครบ';h+=`<td><span class="cell ${{c}}" title="P/V ${{r.pv2==null?'—':r.pv2.toFixed(2)}} · ด่าน ${{r.gate?'ผ่าน':'ไม่ผ่าน'}} · คะแนนเดิม ${{r.tot1.toFixed(1)}}">${{txt}}</span></td>`}}h+='</tr>'}}
$('hm').innerHTML=h+'<tr><td colspan="11" class="muted" style="text-align:left;white-space:normal">ช่องที่ไม่มีสัญญาณแสดง P/V (ราคา ÷ มูลค่า Graham) ของปีนั้น</td></tr>'}})();
// per-signal table
(()=>{{let h='<tr><th>ปี</th><th>หุ้น</th><th>ระดับ</th><th>P/V</th><th>1 ปี</th><th>S&amp;P 1 ปี</th><th>3 ปี</th><th>S&amp;P 3 ปี</th><th>ชนะ 3 ปี?</th><th>ถึง พ.ย. 2026</th><th>S&amp;P</th></tr>';
for(const s of D.sigs){{const w=s.r3==null?'—':(s.r3>s.sp3?'✓':'✗');h+=`<tr><td>${{s.y}}</td><td><b>${{s.t}}</b></td><td><span class="badge ${{s.tier==1?'b-good':'b-warn'}}">${{s.tier==1?'1 เต็ม':'2 ทยอย'}}</span></td><td>${{s.pv.toFixed(2)}}×</td><td class="${{cls(s.r1)}}">${{P(s.r1)}}</td><td>${{P(s.sp1)}}</td><td class="${{cls(s.r3)}}"><b>${{P(s.r3)}}</b></td><td>${{P(s.sp3)}}</td><td>${{w}}</td><td>${{P(s.rN)}}</td><td>${{P(s.spN)}}</td></tr>`}}
$('stbl').innerHTML=h}})();
</script>
</body>
</html>
'''
open('../../output/reports/back-test-10-yr.html', 'w', encoding='utf-8').write(html)
print('ok', len(html))
