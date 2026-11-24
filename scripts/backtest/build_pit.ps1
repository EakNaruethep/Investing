# Builds output/reports/2026-11-18-graham-backtest-pit.html from output/backtest_pit.json
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$json = [IO.File]::ReadAllText((Join-Path $root 'output\backtest_pit.json'))
$tpl = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'pit_template.html'))
$html = $tpl.Replace('/*DATA*/null', $json)
$out = Join-Path $root 'output\reports\2026-11-18-graham-backtest-pit.html'
[IO.File]::WriteAllText($out, $html, (New-Object Text.UTF8Encoding $false))
"wrote $out ($((Get-Item $out).Length) bytes)"
