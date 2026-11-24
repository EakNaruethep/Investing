# Daily price check (no Claude, no tokens): compares today's prices with the buy prices from the
# weekly report (data/watchlist.json) and writes output/reports/daily-report.html. PC version of price_watch.py.
# Usage: powershell -File scripts/dashboard/price_watch.ps1 [-CopyTo <folder>]   (e.g. a OneDrive folder to read it on the phone)
param([string]$CopyTo = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$W = Get-Content (Join-Path $root 'data\watchlist.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$aaa = [double]$W.aaa; $yld = [double]$W.yld
function cl($v, $a = 0.0, $b = 10.0) { [Math]::Max([double]$a, [Math]::Min([double]$b, [double]$v)) }

function Quote($sym) {
  # latest trade at the minute this runs, including pre-market and after-hours (1-minute bars)
  $h = @{ 'User-Agent' = 'Mozilla/5.0' }
  for ($try = 1; $try -le 3; $try++) {
    try {
      $m = (Invoke-RestMethod -Uri "https://query1.finance.yahoo.com/v8/finance/chart/$($sym)?range=1d&interval=1m&includePrePost=true" -Headers $h -TimeoutSec 20).chart.result[0]
      $d = (Invoke-RestMethod -Uri "https://query1.finance.yahoo.com/v8/finance/chart/$($sym)?range=1mo&interval=1d" -Headers $h -TimeoutSec 20).chart.result[0]
      $c = $m.indicators.quote[0].close; $ts = $m.timestamp; $k = $ts.Count - 1
      while ($k -ge 0 -and $null -eq $c[$k]) { $k-- }
      if ($k -ge 0) { $price = [double]$c[$k]; $tsec = [long]$ts[$k] } else { $price = [double]$m.meta.regularMarketPrice; $tsec = [long]$m.meta.regularMarketTime }
      $tp = $m.meta.currentTradingPeriod
      $sess = if ($tsec -lt $tp.regular.start) { 'ก่อนตลาดเปิด' } elseif ($tsec -lt $tp.regular.end) { 'ระหว่างวัน' } else { 'หลังตลาดปิด' }
      if ($tsec -ge $tp.regular.end - 60 -and $tsec -lt $tp.regular.end + 60) { $sess = 'ราคาปิด' }
      $closes = @(); $cs = $d.indicators.quote[0].close
      for ($i = 0; $i -lt $d.timestamp.Count; $i++) { if ($null -ne $cs[$i]) { $closes += [double]$cs[$i] } }
      # previous close = last daily close dated before the latest trade's date (exchange time).
      # meta.chartPreviousClose of the 1-day chart is not reliable for this.
      $off = [TimeSpan]::FromSeconds([double]$d.meta.gmtoffset)
      $tradeDay = [DateTimeOffset]::FromUnixTimeSeconds($tsec).ToOffset($off).Date
      $prev = $null
      for ($i = 0; $i -lt $d.timestamp.Count; $i++) {
        if ($null -ne $cs[$i] -and [DateTimeOffset]::FromUnixTimeSeconds([long]$d.timestamp[$i]).ToOffset($off).Date -lt $tradeDay) { $prev = [double]$cs[$i] }
      }
      $when = [DateTimeOffset]::FromUnixTimeSeconds($tsec).ToOffset([TimeSpan]::FromHours(7)).ToString('d MMM HH:mm', [Globalization.CultureInfo]'th-TH')
      return @{ price = $price; prev = $prev; closes = $closes; when = $when; sess = $sess }
    } catch { Start-Sleep -Seconds (2 * $try) }
  }
  return $null
}

$rows = @()
foreach ($s in $W.stocks) {
  $q = if ($s.yahoo) { Quote $s.yahoo } else { $null }
  $r = [ordered]@{ t = $s.t; name = $s.name; price = $null; chg = $null; pv = $null; buy = $s.buy; buy2 = $null; gap = $null; status = 'na'; why = ''; spark = @() }
  if ($null -eq $q) { $r.why = if ($s.yahoo) { 'ดึงราคาไม่ได้' } else { 'ยังไม่มีราคาซื้อขาย' }; $rows += ,$r; continue }
  $r.price = $q.price; $r.when = $q.when; $r.sess = $q.sess; $r.spark = $q.closes
  if ($q.prev) { $r.chg = $q.price / $q.prev - 1 }
  if ($s.na -or -not $s.V) { $r.why = 'EPS ติดลบ ใช้สูตรไม่ได้'; $rows += ,$r; continue }
  $V = [double]$s.V; $buy = [double]$s.buy
  $V2 = $V * $yld / $aaa; $buy2 = 0.7 * $V2           # tier 2 uses the actual Aaa
  $r.buy2 = $buy2; $r.pv = $q.price / $V; $r.gap = $buy / $q.price - 1
  $score = [double]$s.score1 - 0.25 * [double]$s.vs + 0.25 * (cl (10 * (2.0 - $q.price / $V2) / 1.3))
  $block = @(); if ($s.flag) { $block += "ข้อ C: $($s.flagNote)" }; if ($s.hold) { $block += $s.hold }
  if ($q.price -le $buy -and $s.gate -and -not $block.Count) { $r.status = 't1'; $r.why = 'ผ่านด่านคุณภาพทั้ง 3 · ซื้อเต็ม' }
  elseif ($q.price -le $buy2 -and $score -ge 7.5 -and -not $block.Count) { $r.status = 't2'; $r.why = "คะแนนเดิม $('{0:N2}' -f $score) · ทยอยซื้อ 1/3" }
  elseif ($q.price -le [Math]::Max($buy, $buy2)) {
    $r.status = 'blocked'
    $r.why = 'ราคาถึงแล้ว แต่ ' + $(if ($block.Count) { $block -join ' · ' } elseif (-not $s.gate) { "ไม่ผ่านด่านคุณภาพ ($($s.gateNote)) และคะแนนเดิม $('{0:N2}' -f $score) < 7.5" } else { 'ไม่ผ่านเงื่อนไข' })
  }
  elseif ($q.price -le 1.10 * $buy) { $r.status = 'near'; $r.why = 'ห่างราคาซื้อไม่เกิน 10%' + $(if ($block.Count) { ' · ' + ($block -join ' · ') } elseif (-not $s.gate) { " · ด่านคุณภาพ: $($s.gateNote)" } else { '' }) }
  else { $r.status = 'wait'; $r.why = if ($block.Count) { $block -join ' · ' } elseif (-not $s.gate) { "ด่านคุณภาพ: $($s.gateNote)" } else { 'รอราคา' } }
  $rows += ,$r
}
$ivv = Quote 'IVV'

# history (one line per stock per run; lets the weekly review see the path)
$hist = Join-Path $root 'data\price_history.csv'
if (-not (Test-Path $hist)) { 'date,ticker,price,pv,status' | Out-File $hist -Encoding utf8 }
$today = (Get-Date).ToString('yyyy-MM-dd')
foreach ($r in $rows) { if ($r.price) { "$today,$($r.t),$($r.price),$(if ($r.pv) { [Math]::Round($r.pv, 3) }),$($r.status)" | Out-File $hist -Append -Encoding utf8 } }

# ---- HTML ----
$order = @{ t1 = 0; t2 = 1; blocked = 2; near = 3; wait = 4; na = 5 }
$rows = $rows | Sort-Object { $order[$_.status] }, { if ($null -ne $_.gap) { -$_.gap } else { -99 } }
$label = @{ t1 = 'ระดับ 1 ซื้อ'; t2 = 'ระดับ 2 ซื้อ 1/3'; blocked = 'ถึงราคา แต่ติดเงื่อนไข'; near = 'ใกล้ราคาซื้อ'; wait = 'รอ'; na = 'ไม่ประเมิน' }
function fmt($v, $d = 2) { if ($null -eq $v) { '–' } else { $v.ToString("N$d") } }
function pc($v) { if ($null -eq $v) { '–' } else { ('{0}{1:N1}%' -f $(if ($v -ge 0) { '+' } else { '' }), ($v * 100)) } }
function spark($c) {
  if ($c.Count -lt 2) { return '' }
  $mn = ($c | Measure-Object -Minimum).Minimum; $mx = ($c | Measure-Object -Maximum).Maximum; if ($mx -eq $mn) { $mx = $mn + 1 }
  $pts = for ($i = 0; $i -lt $c.Count; $i++) { '{0:N1},{1:N1}' -f (2 + $i * 96 / ($c.Count - 1)), (22 - ($c[$i] - $mn) / ($mx - $mn) * 18) }
  $up = $c[-1] -ge $c[0]
  "<svg viewBox='0 0 100 26' class='sp' aria-hidden='true'><polyline points='$(($pts -join ' ').Replace(', ', ','))' fill='none' stroke='var($(if ($up) { '--up' } else { '--down' }))' stroke-width='1.6'/></svg>"
}
$sig = @($rows | Where-Object { $_.status -in 't1', 't2' })
$banner = if ($sig.Count) { "<div class='banner hit'><b>มีสัญญาณซื้อ:</b> " + (($sig | ForEach-Object { "$($_.t) ($($label[$_.status]))" }) -join ', ') + ' · ตรวจข่าวล่าสุดก่อนซื้อ (ข้อ D)</div>' }
          else { "<div class='banner'>ยังไม่มีสัญญาณซื้อ · เงินใหม่อยู่ใน IVV" + $(if ($ivv) { " (IVV $(fmt $ivv.price) $(pc ($ivv.price / $ivv.prev - 1)))" }) + '</div>' }
$age = ((Get-Date) - [datetime]$W.builtAt).TotalDays
$stale = if ($age -gt 8) { "<div class='banner warn'>ราคาซื้อมาจากการทบทวนเมื่อ $([Math]::Floor($age)) วันก่อน · ควรรันรอบประจำสัปดาห์</div>" } else { '' }
$trs = foreach ($r in $rows) {
  "<tr class='s-$($r.status)'><td><b>$($r.t)</b><span class='nm'>$($r.name)</span></td><td class='n'>$(fmt $r.price)<span class='nm $(if ($r.chg -lt 0) { 'dn' } else { 'up' })'>$(pc $r.chg)</span><span class='nm'>$($r.sess) $($r.when)</span></td><td>$(spark $r.spark)</td><td class='n'>$(fmt $r.buy)</td><td class='n'>$(if ($null -eq $r.gap) { '–' } elseif ($r.gap -ge 0) { 'ถึงแล้ว' } else { pc $r.gap })</td><td class='n'>$(if ($r.pv) { (fmt $r.pv) + '×' } else { '–' })</td><td><span class='pill p-$($r.status)'>$($label[$r.status])</span><span class='why'>$($r.why)</span></td></tr>"
}
$css = @'
:root{--bg:#f5f7f6;--surface:#fff;--ink:#17211d;--muted:#5d6b65;--line:#dde4e0;--accent:#1e6b52;--up:#1e7a4a;--down:#b3261e;--t1:#1e6b52;--t1s:#d6ede3;--t2:#9a6a12;--t2s:#f5e8cc;--bl:#8a4b9a;--bls:#efe2f3;--nr:#2b5c9e;--nrs:#dde8f6;--wt:#5d6b65;--wts:#eceff0;--f:"IBM Plex Sans Thai","Leelawadee UI",system-ui,sans-serif;--m:"IBM Plex Mono",Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#101513;--surface:#17201c;--ink:#e3ebe7;--muted:#97a6a0;--line:#2a3631;--accent:#5fc49b;--up:#5fc49b;--down:#f2827a;--t1:#5fc49b;--t1s:#193a2e;--t2:#e6b45a;--t2s:#3a2e17;--bl:#d09ae0;--bls:#33243a;--nr:#8db6ee;--nrs:#1d2e45;--wt:#97a6a0;--wts:#222c28;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#101513;--surface:#17201c;--ink:#e3ebe7;--muted:#97a6a0;--line:#2a3631;--accent:#5fc49b;--up:#5fc49b;--down:#f2827a;--t1:#5fc49b;--t1s:#193a2e;--t2:#e6b45a;--t2s:#3a2e17;--bl:#d09ae0;--bls:#33243a;--nr:#8db6ee;--nrs:#1d2e45;--wt:#97a6a0;--wts:#222c28;color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f);font-size:15px;line-height:1.55}
.wrap{max-width:900px;margin:0 auto;padding-block:20px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:14px}
h1{margin:0;font-size:1.35rem}.sub{color:var(--muted);font-size:.85rem}
.banner{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.banner.hit{background:var(--t1s);border-color:var(--t1);color:var(--t1)}.banner.warn{background:var(--t2s);border-color:var(--t2);color:var(--t2)}
.scroll{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:.88rem}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{color:var(--muted);font-size:.78rem;font-weight:600;white-space:nowrap}tr:last-child td{border-bottom:0}
td.n{text-align:right;font-family:var(--m);font-variant-numeric:tabular-nums;white-space:nowrap}
.nm{display:block;color:var(--muted);font-size:.75rem;font-family:var(--f)}.nm.up{color:var(--up)}.nm.dn{color:var(--down)}
.sp{width:90px;height:26px;display:block}
.pill{display:inline-block;border-radius:999px;padding:0 8px;font-size:.78rem;font-weight:600;white-space:nowrap}
.p-t1{background:var(--t1s);color:var(--t1)}.p-t2{background:var(--t2s);color:var(--t2)}.p-blocked{background:var(--bls);color:var(--bl)}.p-near{background:var(--nrs);color:var(--nr)}.p-wait,.p-na{background:var(--wts);color:var(--wt)}
.why{display:block;color:var(--muted);font-size:.78rem;min-width:220px;max-width:340px}
footer{color:var(--muted);font-size:.78rem}
'@
$now = (Get-Date).ToString('yyyy-MM-dd HH:mm')
$html = @"
<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>รายงานราคารายวัน</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;600&family=IBM+Plex+Mono&display=swap"><style>$css</style></head><body><div class="wrap">
<header><h1>รายงานราคารายวัน</h1><div class="sub">อัปเดต $now (เวลาไทย) · ราคาซื้อขายล่าสุด ณ นาทีที่รัน รวมช่วงก่อนตลาดเปิดและหลังตลาดปิด (Yahoo) · % เทียบราคาปิดวันก่อน · ราคาซื้อจากการทบทวนรายสัปดาห์ $($W.builtAt) (ราคาในรายงาน $($W.reportAsOf)) · Aaa $($aaa)%</div></header>
$banner$stale
<div class="scroll"><table><thead><tr><th>หุ้น</th><th style="text-align:right">ราคา</th><th>1 เดือน</th><th style="text-align:right">ราคาซื้อ</th><th style="text-align:right">ต้องลงอีก</th><th style="text-align:right">ราคา/มูลค่า</th><th>สถานะ</th></tr></thead><tbody>
$($trs -join "`n")
</tbody></table></div>
<footer>หน้านี้เช็คแค่ข้อ A (ราคา) ส่วนข้อ B, C, D ใช้ผลจากการทบทวนรายสัปดาห์ · ระดับ 2 ใช้ราคาซื้อที่คิดด้วย Aaa จริงและคะแนนเดิมที่ราคาวันนี้ · "ต้องลงอีก" = ราคาซื้อ ÷ ราคาวันนี้ − 1 · ไม่ใช่คำแนะนำการลงทุน</footer>
</div></body></html>
"@
$outFile = Join-Path $root 'output\reports\daily-report.html'
[IO.File]::WriteAllText($outFile, $html, (New-Object Text.UTF8Encoding $false))
if ($CopyTo) { Copy-Item $outFile (Join-Path $CopyTo 'graham-daily.html') -Force }
foreach ($r in $rows) { '{0,-5} {1,9} {2,-8} {3}' -f $r.t, (fmt $r.price), $r.status, $r.why }
"wrote $outFile"
