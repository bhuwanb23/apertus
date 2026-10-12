$ErrorActionPreference = 'Stop'
$root = 'D:\projects\ml\apertus'
$items = [System.IO.File]::ReadAllText((Join-Path $root 'data\dialect\items_D001_D017.json'), [System.Text.Encoding]::UTF8) | ConvertFrom-Json

$files = @{}
foreach ($f in Get-ChildItem (Join-Path $root 'data\sources\raw_pages') -Filter 'S05*.txt') {
  $lines = Get-Content -LiteralPath $f.FullName -Encoding UTF8
  $url = $null
  foreach ($l in $lines) { if ($l.StartsWith('URL: ')) { $url = $l.Substring(5); break } }
  $files[$f.BaseName.Substring(0,4) + '|' + $url] = $lines
}

$fail = 0
foreach ($it in $items) {
  if ($it.task_type -ne 'translation') { continue }
  $lines = $files[$it.source_id + '|' + $it.source_url]

  # Build positional index: Nth VERBATIM sentence  <->  Sn. reference, by document order.
  $vpos = @(); $rpos = @{}
  $insideV = $false
  foreach ($l in $lines) {
    if ($l -match '^=== VERBATIM SWISS GERMAN SENTENCES ===') { $insideV = $true; continue }
    if ($l -match '^=== STANDARD GERMAN TRANSLATIONS') { $insideV = $false; $insideR = $true; continue }
    if ($l -match '^===') { $insideV = $false; if ($lines.IndexOf($l) -lt 0) { } }
    if ($insideV -and $l.StartsWith('"')) { $vpos += ,$l.Substring(1, $l.Length - 2) }
    if ($l -match '^S(\d+)\.\s*"(.*)"\s*$' -and -not $insideV) {
      # S056 style: S1. "a" -> "b"   |   S057 style: S1. "b"
      $full = $Matches[0]
      $arrow = [char]0x2192
      if ($full.Contains($arrow)) {
        $tail = $full.Substring($full.LastIndexOf($arrow) + 1).Trim()
        if ($tail.StartsWith('"') -and $tail.EndsWith('"')) { $rpos[[int]$Matches[1]] = $tail.Substring(1, $tail.Length - 2) }
      } else {
        $rpos[[int]$Matches[1]] = $Matches[2]
      }
    }
  }

  $n = [array]::IndexOf($vpos, $it.swiss_german_text)
  if ($n -lt 0) { $fail++; Write-Output ("FAIL  {0}  sentence not found" -f $it.id); continue }
  $sn = $n + 1
  $expRef = $rpos[$sn]
  $ok = ($expRef -eq $it.standard_german_reference)
  $tag = if ($ok) { 'PASS' } else { $fail++; 'FAIL' }
  Write-Output ("{0}  {1}  VERBATIM[{2}] == {3}. reference {4}" -f $tag, $it.id, $sn, $it.source_id, $(if ($ok) { 'matches' } else { "MISMATCH -> expected: $expRef" }))
}
Write-Output ""
Write-Output ("TOTAL FAILURES: " + $fail)