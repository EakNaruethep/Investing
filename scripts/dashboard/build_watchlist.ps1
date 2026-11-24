# Weekly step (after the full report is refreshed): pull the valuation numbers out of the main report
# into data/watchlist.json, the small file the daily price check reads. Costs no Claude tokens.
# Usage: powershell -File scripts/dashboard/build_watchlist.ps1 [-Report <path to valuation html>]
param([string]$Report = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $Report) { $Report = Join-Path $root 'output\reports\2026-11-16-graham-mag7-valuation.html' }
$h = [IO.File]::ReadAllText($Report, [Text.Encoding]::UTF8)

# the report keeps its per-stock data in a JS object literal "S={...}"
$i = $h.IndexOf('S={'); if ($i -lt 0) { throw "No S={...} data block in $Report" }
$i += 2; $d = 0
for ($k = $i; $k -lt $h.Length; $k++) { $c = $h[$k]; if ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { break } } }
$S = $h.Substring($i, $k - $i + 1) | ConvertFrom-Json

$aaa = [double]([regex]::Match($h, 'Aaa ต.ค. (\d{4}) = ([\d.]+)%').Groups[2].Value)
if (-not $aaa) { $aaa = [double]([regex]::Match($h, 'Aaa[^0-9]{0,40}([\d.]+)%').Groups[1].Value) }
$asOf = [regex]::Match($h, 'ราคาปิด ([^·<]+)').Groups[1].Value.Trim()

# news holds (check D) are judged by hand in the weekly review; kept in data/d_holds.json
$holdsPath = Join-Path $root 'data\d_holds.json'
$holds = if (Test-Path $holdsPath) { Get-Content $holdsPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { [pscustomobject]@{} }

$yahoo = @{}   # ticker -> Yahoo symbol when they differ
$list = @()
foreach ($p in $S.PSObject.Properties) {
  $x = $p.Value; $t = $p.Name
  $list += [ordered]@{
    t = $t; yahoo = if ($yahoo.ContainsKey($t)) { $yahoo[$t] } else { $t }; name = $x.name
    V = $x.V; buy = $x.buy; eps = $x.eps; g = $x.g; na = [bool]$x.na
    gate = [bool]$x.gate; gateNote = $x.gw; flag = [bool]$x.flag; flagNote = $x.fw
    score1 = $x.total1; vs = $x.vs; q = $x.q; cf = $x.cf; bs = $x.bs
    hold = if ($holds.PSObject.Properties[$t]) { $holds.$t } else { '' }
    reportPrice = $x.price
  }
}
$out = [ordered]@{ builtAt = (Get-Date).ToString('yyyy-MM-dd HH:mm'); reportAsOf = $asOf; aaa = $aaa; yld = [Math]::Max($aaa, 4.4)
  report = [IO.Path]::GetFileName($Report); stocks = $list }
$path = Join-Path $root 'data\watchlist.json'
[IO.File]::WriteAllText($path, ($out | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
"wrote $path ($($list.Count) stocks, Aaa $aaa%)"
