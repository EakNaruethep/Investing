# Point-in-time backtest of the two-tier buy rules (CLAUDE.md), Nov 2015 - Nov 2026.
# Uses only 10-K data whose "filed" date is on or before each decision date (no look-ahead),
# on a universe fixed at the start (largest US companies around 2015), not picked with hindsight.
# Run:  powershell -File pit_backtest.ps1   (writes ..\..\output\backtest_pit.json)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$data = Join-Path $root 'data'
Add-Type -AssemblyName System.Web.Extensions
function Load($p) { $s = New-Object System.Web.Script.Serialization.JavaScriptSerializer; $s.MaxJsonLength = [int]::MaxValue; $s.RecursionLimit = 1000; $s.DeserializeObject([IO.File]::ReadAllText($p)) }

$inp = Load (Join-Path $data 'backtest_inputs.json')
$TICKERS = 'AAPL','MSFT','GOOGL','AMZN','BRK','XOM','GE','JNJ','WFC','JPM'
$PTMAP = @{ BRK = 'BRK-B' }
$DECISION_YEARS = 2015..2025
$SPIN = @('GE|2023-01-04', 'GE|2024-04-02')   # spin-offs Yahoo records as splits: adjust price, not EPS

# ---------- SEC point-in-time series ----------
$facts = @{}
foreach ($t in $TICKERS) {
  $g = (Load "$data\sec\$t.json")['facts']['us-gaap']
  if ($t -eq 'GOOGL') { $facts['GOOGL_old'] = (Load "$data\sec\GOOGL_old.json")['facts']['us-gaap'] }
  $facts[$t] = $g
}
function Entries($t, $c) {
  $list = @()
  $srcs = if ($t -eq 'GOOGL') { @($facts['GOOGL'], $facts['GOOGL_old']) } else { @($facts[$t]) }
  foreach ($g in $srcs) {
    if (-not $g.ContainsKey($c)) { continue }
    foreach ($u in $g[$c]['units'].Keys) { foreach ($e in $g[$c]['units'][$u]) { if ($e['form'] -eq '10-K' -or $e['form'] -eq '10-K/A') { $list += ,$e } } }
  }
  return $list
}
$cache = @{}
function Series($t, $c, $flow) {
  $k = "$t|$c"
  if (-not $cache.ContainsKey($k)) {
    $rows = @()
    foreach ($e in (Entries $t $c)) {
      if ($flow) { if (-not $e['start']) { continue }; $d = ([datetime]$e['end'] - [datetime]$e['start']).TotalDays; if ($d -lt 330 -or $d -gt 380) { continue } }
      elseif ($e['start']) { continue }
      $rows += ,@{ end = [string]$e['end']; filed = [string]$e['filed']; val = [double]$e['val'] }
    }
    $cache[$k] = $rows
  }
  return $cache[$k]
}
# value of concept for each fiscal-year end, as known on date D (latest filing filed <= D)
function Known($t, $c, $flow, $D) {
  $best = @{}
  foreach ($r in (Series $t $c $flow)) {
    if ($r.filed -gt $D) { continue }
    if (-not $best.ContainsKey($r.end) -or $r.filed -gt $best[$r.end].filed) { $best[$r.end] = $r }
  }
  return $best
}
function KnownAny($t, $concepts, $flow, $D, $mode) {
  # mode 'first' = first concept in priority order that has the end date; 'max' = largest across concepts
  $out = @{}
  foreach ($c in $concepts) {
    $k = Known $t $c $flow $D
    foreach ($e in $k.Keys) {
      if (-not $out.ContainsKey($e)) { $out[$e] = $k[$e] }
      elseif ($mode -eq 'max' -and $k[$e].val -gt $out[$e].val) { $out[$e] = $k[$e] }
    }
  }
  return $out
}
function SplitFactor($t, $after, $upto, $forEps) {
  $f = 1.0; $pt = if ($PTMAP.ContainsKey($t)) { $PTMAP[$t] } else { $t }
  foreach ($s in $inp['splits'][$pt]) {
    if ($forEps -and ($SPIN -contains "$t|$($s['date'])")) { continue }
    if ($s['date'] -gt $after -and $s['date'] -le $upto) { $f *= [double]$s['numerator'] / [double]$s['denominator'] }
  }
  return $f
}
function cl($v, $a = 0.0, $b = 10.0) { [Math]::Max([double]$a, [Math]::Min([double]$b, [double]$v)) }

$C = @{
  eps   = @('EarningsPerShareDiluted', 'EarningsPerShareBasic')
  ni    = @('NetIncomeLoss')
  op    = @('OperatingIncomeLoss')
  pti   = @('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments')
  rev   = @('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'RevenuesNetOfInterestExpense')
  ocf   = @('NetCashProvidedByUsedInOperatingActivities', 'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations')
  capex = @('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets')
  sh    = @('WeightedAverageNumberOfDilutedSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic')
  eq    = @('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
  cash  = @('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents')
  cashsti = @('CashCashEquivalentsAndShortTermInvestments')
  sti   = @('MarketableSecuritiesCurrent', 'AvailableForSaleSecuritiesDebtSecuritiesCurrent', 'AvailableForSaleSecuritiesCurrent', 'ShortTermInvestments')
  lti   = @('MarketableSecuritiesNoncurrent')
  ltd   = @('LongTermDebt')
  ltdn  = @('LongTermDebtNoncurrent')
  ltdc  = @('LongTermDebtCurrent')
  std   = @('ShortTermBorrowings', 'CommercialPaper')
  dc    = @('DebtCurrent')
}
function V($h, $e) { if ($h.ContainsKey($e)) { $h[$e].val } else { $null } }

function Evaluate($t, $y) {
  $pt = if ($PTMAP.ContainsKey($t)) { $PTMAP[$t] } else { $t }
  $px = $inp['prices'][$pt]["$y"]; $D = [string]$px['date']
  $ni = KnownAny $t $C.ni $true $D 'first'
  $ends = @($ni.Keys | Sort-Object)
  $last = $ends[-1]
  # ---- EPS history (split-adjusted to the share basis on date D) ----
  $epsK = KnownAny $t $C.eps $true $D 'first'
  $shK = KnownAny $t $C.sh $true $D 'first'
  # share counts (on the basis of date D) per fiscal year: reported weighted-average shares,
  # else implied by NI / EPS. Years whose EPS is missing (dimensional tags: Alphabet 2015-16, BRK after 2014)
  # use NI / shares of the nearest fiscal year that has a share count.
  $shares = @{}
  foreach ($e in $ends) {
    if ($shK.ContainsKey($e) -and $shK[$e].val -gt 0) {
      $sv = $shK[$e].val; if ($t -eq 'BRK' -and $sv -gt 1e9) { $sv = $sv / 1e6 }   # BRK 2011 10-K tagged shares x1e6
      $shares[$e] = $sv * (SplitFactor $t $shK[$e].filed $D $true)
    }
    elseif ($epsK.ContainsKey($e) -and $epsK[$e].val -ne 0) { $shares[$e] = $ni[$e].val / ($epsK[$e].val / (SplitFactor $t $epsK[$e].filed $D $true)) }
  }
  $eps = @{}; $epsSrc = @{}
  foreach ($e in $ends) {
    if ($epsK.ContainsKey($e)) { $r = $epsK[$e]; $eps[$e] = $r.val / (SplitFactor $t $r.filed $D $true); $epsSrc[$e] = 'reported' }
    elseif ($shares.Count) {
      $near = $shares.Keys | Sort-Object { [Math]::Abs(([datetime]$_ - [datetime]$e).TotalDays) } | Select-Object -First 1
      $eps[$e] = $ni[$e].val / $shares[$near]; $epsSrc[$e] = "NI/shares($($near.Substring(0,4)))"
    }
  }
  $epsLastSrc = $epsSrc[$last]
  if ($t -eq 'BRK') { foreach ($e in @($eps.Keys)) { $eps[$e] = $eps[$e] / 1500 } }   # Class A -> Class B
  $hist = @($ends | Where-Object { $eps.ContainsKey($_) } | ForEach-Object { $eps[$_] })
  $n = $hist.Count
  $e3 = $hist[$n - 1]; $e0 = if ($n -ge 4) { $hist[$n - 4] } else { $null }; $e5 = if ($n -ge 6) { $hist[$n - 6] } else { $null }
  $eRep = $e3; $capped = $false
  if ($script:GUARD -and $n -ge 4) {
    # one-off guard (rule-based, no hindsight): cap the latest EPS at 1.5x the median of the 3 prior years
    $med = ($hist[($n - 4)..($n - 2)] | Sort-Object)[1]
    if ($med -gt 0 -and $e3 -gt 1.5 * $med) { $e3 = 1.5 * $med; $capped = $true }
  }
  $cagr = if ($e0 -gt 0 -and $e3 -gt 0) { [Math]::Pow($e3 / $e0, 1 / 3) - 1 } else { $null }
  $cagr5 = if ($e5 -gt 0 -and $e3 -gt 0) { [Math]::Pow($e3 / $e5, 1 / 5) - 1 } else { $null }
  $gg = if ($null -eq $cagr) { if ($e3 -gt 0) { 15.0 } else { $null } } else { cl (0.75 * $cagr * 100) 0 15 }
  $fast = ($null -eq $cagr) -or ($cagr -gt 0.40 -and ($null -eq $cagr5 -or $cagr5 -gt 0.40))
  $min3 = ($hist[($n - 3)..($n - 1)] | Measure-Object -Minimum).Minimum
  $flag = $fast -or ($min3 -le 0)
  # ---- ratios from the latest 10-K known on D ----
  $rev = V (KnownAny $t $C.rev $true $D 'max') $last
  $op = V (KnownAny $t $C.op $true $D 'first') $last
  $opSrc = 'op'
  if ($null -eq $op) { $op = V (KnownAny $t $C.pti $true $D 'first') $last; $opSrc = 'pretax' }
  $niL = $ni[$last].val
  $ocf = V (KnownAny $t $C.ocf $true $D 'first') $last
  $capex = V (KnownAny $t $C.capex $true $D 'max') $last; if ($null -eq $capex) { $capex = 0 }
  $eq = V (KnownAny $t $C.eq $false $D 'first') $last
  $cs = V (KnownAny $t $C.cashsti $false $D 'first') $last
  if ($null -eq $cs) { $cs = [double](V (KnownAny $t $C.cash $false $D 'first') $last) + [double](V (KnownAny $t $C.sti $false $D 'first') $last) }
  $cs += [double](V (KnownAny $t $C.lti $false $D 'first') $last)
  $ltd = V (KnownAny $t $C.ltd $false $D 'first') $last
  $ltdc = V (KnownAny $t $C.ltdc $false $D 'first') $last
  if ($null -eq $ltd) { $ltd = [double](V (KnownAny $t $C.ltdn $false $D 'first') $last) + [double]$ltdc }
  $std = V (KnownAny $t $C.std $false $D 'first') $last
  if ($null -eq $std) { $dc = V (KnownAny $t $C.dc $false $D 'first') $last; $std = if ($null -ne $dc) { [Math]::Max(0.0, $dc - [double]$ltdc) } else { 0 } }
  $debt = $ltd + $std
  $fcf = if ($null -ne $ocf) { $ocf - $capex } else { $null }
  $opm = if ($rev -gt 0 -and $null -ne $op) { $op / $rev } else { 0 }
  $roe = if ($eq -gt 0) { $niL / $eq } else { 0 }
  $conv = if ($niL -gt 0 -and $null -ne $fcf) { $fcf / $niL } else { -1 }
  $fm = if ($rev -gt 0 -and $null -ne $fcf) { $fcf / $rev } else { 0 }
  $nd = if ($ocf -gt 0) { ($debt - $cs) / $ocf } else { 3 }
  $ret = if ($ocf -gt 0) { $fcf / $ocf } else { -1 }
  $q = 0.5 * (cl ($opm / 0.4 * 10)) + 0.5 * (cl ($roe / 0.35 * 10))
  $cf = 0.5 * (cl ($conv * 10)) + 0.5 * (cl ($fm / 0.25 * 10))
  $bs = if (($debt - $cs) -le 0) { 10 } else { cl (10 - 2.5 * $nd) }
  $core = cl ($ret / 0.6 * 10)
  $gate = ($q -ge 6) -and ($cf -ge 5) -and ($bs -ge 5)
  # ---- valuation (raw price on D = Yahoo split-adjusted close x later split factors) ----
  $price = [double]$px['close'] * (SplitFactor $t $D '9999-12-31' $false)
  $aaa = [double]$inp['aaa']["$y"]
  $res = @{}
  foreach ($mode in 'v2', 'v1') {
    $Yl = if ($mode -eq 'v2') { [Math]::Max($aaa, 4.4) } else { $aaa }
    if ($e3 -le 0 -or $null -eq $gg) { $Vv = $null; $pv = $null } else { $Vv = $e3 * (8.5 + 2 * $gg) * 4.4 / $Yl; $pv = $price / $Vv }
    $vs = if ($null -eq $pv) { 0 } else { cl (10 * (2.0 - $pv) / 1.3) }
    $tot1 = 0.25 * $vs + 0.25 * $q + 0.20 * $cf + 0.15 * $bs + 0.15 * $core
    $tot2 = 0.40 * $vs + 0.20 * $q + 0.15 * $cf + 0.15 * $bs + 0.10 * $core
    $res[$mode] = @{ Y = $Yl; V = $Vv; pv = $pv; tot1 = $tot1; tot2 = $tot2 }
  }
  $t1 = ($null -ne $res.v2.pv) -and $res.v2.pv -le 0.70 -and $gate -and -not $flag
  $t2 = (-not $t1) -and ($null -ne $res.v1.pv) -and $res.v1.pv -le 0.70 -and $res.v1.tot1 -ge 7.5 -and -not $flag
  return [ordered]@{ t = $t; y = $y; date = $D; fy = $last; price = $price; eps = $e3; g = $gg; cagr3 = $cagr; cagr5 = $cagr5; flag = $flag
    V = $res.v2.V; buy = if ($res.v2.V) { 0.7 * $res.v2.V } else { $null }; pv = $res.v2.pv; pvA = $res.v1.pv; yld = $res.v2.Y; aaa = $aaa
    opm = $opm; opSrc = $opSrc; roe = $roe; conv = $conv; fm = $fm; nd = $nd; netcash = (($debt - $cs) -le 0)
    q = $q; cf = $cf; bs = $bs; core = $core; gate = $gate; tot1 = $res.v1.tot1; tot2 = $res.v2.tot2
    tier = if ($t1) { 1 } elseif ($t2) { 2 } else { 0 }; epsHist = $hist; epsSrc = $epsLastSrc; epsRep = $eRep; capped = $capped }
}

function Adj($pt, $y) { [double]$inp['prices'][$pt]["$y"]['adjclose'] }
function Fwd($t, $y, $n) { $pt = if ($PTMAP.ContainsKey($t)) { $PTMAP[$t] } else { $t }; if ($y + $n -gt 2026) { return $null }; (Adj $pt ($y + $n)) / (Adj $pt $y) - 1 }

function RunAll($guard) {
  $script:GUARD = $guard
$rows = @(); $years = @()
$v = @{ tier = @(100.0); spy = @(100.0); ew = @(100.0); v1 = @(100.0) }
foreach ($y in $DECISION_YEARS) {
  $yr = @()
  foreach ($t in $TICKERS) {
    $r = Evaluate $t $y
    $r.r1 = Fwd $t $y 1; $r.r3 = Fwd $t $y 3; $r.rN = Fwd $t $y (2026 - $y)
    $yr += ,$r; $rows += ,$r
  }
  $sp1 = Fwd 'SPY' $y 1; $sp3 = Fwd 'SPY' $y 3; $spN = Fwd 'SPY' $y (2026 - $y)
  $w = @{}; foreach ($r in $yr) { if ($r.tier -eq 1) { $w[$r.t] = 1.0 } elseif ($r.tier -eq 2) { $w[$r.t] = 1 / 3 } }
  $s = ($w.Values | Measure-Object -Sum).Sum; if (-not $s) { $s = 0 }
  if ($s -ge 1) { foreach ($k in @($w.Keys)) { $w[$k] = $w[$k] / $s }; $cash = 0.0 } else { $cash = 1 - $s }
  $port = { param($n, $spx) $acc = $cash * $spx; foreach ($k in $w.Keys) { $acc += $w[$k] * ($yr | Where-Object { $_.t -eq $k })."r$n" }; $acc }
  $p1 = & $port 1 $sp1; $p3 = if ($null -ne $sp3) { & $port 3 $sp3 } else { $null }; $pN = & $port 'N' $spN
  # old single-score rule (v1): P/V<=0.7 with actual Aaa and 25/25/20/15/15 score >= 7.5, equal weight, else SPY
  $old = @($yr | Where-Object { $null -ne $_.pvA -and $_.pvA -le 0.70 -and $_.tot1 -ge 7.5 })
  $o1 = if ($old.Count) { ($old | ForEach-Object { $_.r1 } | Measure-Object -Average).Average } else { $sp1 }
  $ew1 = ($yr | ForEach-Object { $_.r1 } | Measure-Object -Average).Average
  $v.tier += $v.tier[-1] * (1 + $p1); $v.spy += $v.spy[-1] * (1 + $sp1); $v.ew += $v.ew[-1] * (1 + $ew1); $v.v1 += $v.v1[-1] * (1 + $o1)
  $years += ,[ordered]@{ y = $y; date = $yr[0].date; aaa = $yr[0].aaa; yld = $yr[0].yld; w = $w; cash = $cash; p1 = $p1; p3 = $p3; pN = $pN; sp1 = $sp1; sp3 = $sp3; spN = $spN; ew1 = $ew1; v1 = $o1; v1sig = @($old | ForEach-Object { $_.t }) }
}
  return [ordered]@{ years = $years; rows = $rows; curve = $v }
}
$A = RunAll $false; $B = RunAll $true
$rows = $A.rows; $years = $A.years; $v = $A.curve
$out = [ordered]@{ T = $TICKERS; strict = $A; guard = $B }
$json = $out | ConvertTo-Json -Depth 8 -Compress
New-Item -ItemType Directory -Force (Join-Path $root 'output') | Out-Null
[IO.File]::WriteAllText((Join-Path $root 'output\backtest_pit.json'), $json, (New-Object Text.UTF8Encoding $false))
foreach ($r in $rows) {
  '{0} {1,-5} fy {2} px {3,8:N2} eps {4,7:N2} g {5,5:N1} pv {6,5} q {7,4:N1} cf {8,4:N1} bs {9,4:N1} {10}{11} tier {12} r1 {13,6:P0}' -f $r.y, $r.t, $r.fy, $r.price, $r.eps, $r.g, $(if ($r.pv) { '{0:N2}' -f $r.pv } else { '-' }), $r.q, $r.cf, $r.bs, $(if ($r.gate) { 'G' } else { '.' }), $(if ($r.flag) { 'F' } else { '.' }), $r.tier, $r.r1
}
foreach ($k in $B.curve.Keys) { 'guard {0}: {1:N0}' -f $k, $B.curve[$k][-1] }
foreach ($k in $v.Keys) { '{0}: {1:N0}  CAGR {2:P1}' -f $k, $v[$k][-1], ([Math]::Pow($v[$k][-1] / 100, 1 / 11) - 1) }
foreach ($YR in $years) { '{0} picks [{1}] cash {2:N2} 1y {3:P0} vs SPY {4:P0}' -f $YR.y, (($YR.w.Keys | ForEach-Object { "$_ $('{0:N2}' -f $YR.w[$_])" }) -join ', '), $YR.cash, $YR.p1, $YR.sp1 }





