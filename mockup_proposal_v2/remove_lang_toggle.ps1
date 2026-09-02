$ErrorActionPreference = 'Stop'
$base = "H:\ai-campaign-studio-worktrees\SPIKE-001-pywebview-content-studio\mockup_proposal_v2"
$dirs = @("brand", "brief", "plan", "studio", "pregled", "settings")

$pattern = @'
      <div class="flex items-center gap-1 text-xs text-slate-500">
        <span>Jezik</span>
        <button class="px-2 py-0.5 rounded font-medium text-slate-700 hover:bg-slate-100">EN</button>
        <button class="px-2 py-0.5 rounded font-medium bg-slate-900 text-white">BHS</button>
      </div>
'@

foreach ($d in $dirs) {
    $f = Join-Path $base "$d\index.html"
    if (-not (Test-Path $f)) { Write-Host "MISSING: $f"; continue }
    $c = Get-Content $f -Raw -Encoding UTF8
    if ($c.Contains($pattern)) {
        $c2 = $c.Replace($pattern, '')
        Set-Content $f -Value $c2 -Encoding UTF8 -NoNewline
        Write-Host "OK: $d"
    } else {
        Write-Host "NO PATTERN in: $d"
    }
}
