#Requires -Version 5.1
<#
.SYNOPSIS
    Проверка синхронности памяти Rogalik с изменениями кода, ассетов и правил (D12, D13).

.DESCRIPTION
    Ловит типовые промахи перед коммитом и push:
      * изменения в game/ assets/ plugins/ tools/ reports/ без обновления docs/progress/  -> FAIL
      * изменения документов-правил без записи в docs/DECISIONS.md                        -> WARN
      * файлы-секреты в наборе изменений                                                   -> FAIL
      * добавленный файл больше лимитов GitHub (50 MB / 100 MB)                            -> WARN / FAIL

    Код возврата 1 — есть хотя бы одна ошибка (FAIL). Одни предупреждения код не меняют.
    Скрипт ничего не изменяет и не читает содержимое файлов — только пути и размеры.

.PARAMETER Staged
    Проверять только индекс (то, что войдёт в коммит).

.PARAMETER Commit
    Проверять конкретный коммит, например -Commit HEAD.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/git/check-memory-sync.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/git/check-memory-sync.ps1 -Staged

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/git/check-memory-sync.ps1 -Commit HEAD
#>
param(
    [switch]$Staged,
    [string]$Commit = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

function Get-ChangedPaths {
    param([switch]$OnlyStaged, [string]$Ref)

    $raw = @()
    if ($Ref -ne '') {
        $raw = @(git show --pretty=format: --name-only --diff-filter=ACMRD $Ref 2>$null)
    }
    elseif ($OnlyStaged) {
        $raw = @(git diff --cached --name-only --diff-filter=ACMRD)
    }
    else {
        $raw = @(git diff --name-only --diff-filter=ACMRD)
        $raw += @(git diff --cached --name-only --diff-filter=ACMRD)
        $raw += @(git ls-files --others --exclude-standard)
    }

    return @($raw | Where-Object { $_ -ne $null -and $_.Trim() -ne '' } | ForEach-Object { $_.Trim() -replace '\\', '/' } | Sort-Object -Unique)
}

function Test-Prefix {
    param([string]$Path, [string[]]$Prefixes)
    foreach ($p in $Prefixes) {
        if ($Path.StartsWith($p, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

$mode = 'рабочее дерево + индекс'
if ($Commit -ne '') { $mode = "коммит $Commit" }
elseif ($Staged) { $mode = 'индекс (staged)' }

$changed = Get-ChangedPaths -OnlyStaged:$Staged -Ref $Commit
$fail = 0
$warn = 0

Write-Output 'Rogalik — проверка синхронности памяти (D12/D13)'
Write-Output ("режим: {0}; изменённых путей: {1}" -f $mode, $changed.Count)

if ($changed.Count -eq 0) {
    Write-Output '[PASS] изменений нет — проверять нечего'
    exit 0
}

$codePrefixes = @('game/', 'assets/', 'plugins/', 'tools/', 'reports/')
$rulePrefixes = @('AGENTS.md', 'docs/GITHUB_WORKFLOW.md', 'docs/DEVELOPMENT_PLAN.md', 'docs/DEEPSEEK_GAME_DEV_RULES.md')

$hasCode = $false
$hasMemory = $false
$hasDecisions = $false
$hasRules = $false
foreach ($path in $changed) {
    if (Test-Prefix -Path $path -Prefixes $codePrefixes) { $hasCode = $true }
    if (Test-Prefix -Path $path -Prefixes @('docs/progress/')) { $hasMemory = $true }
    if ($path -eq 'docs/DECISIONS.md') { $hasDecisions = $true }
    if (Test-Prefix -Path $path -Prefixes $rulePrefixes) { $hasRules = $true }
}

if ($hasCode -and -not $hasMemory) {
    Write-Output '[FAIL] CODE_WITHOUT_MEMORY: изменены код/ассеты/инструменты, но docs/progress/ не обновлён'
    Write-Output '       обновите docs/progress/STAGE_NN.md (и PROJECT_STATE.md, если изменилось состояние)'
    $fail++
}
elseif ($hasCode) {
    Write-Output '[PASS] MEMORY_UPDATE: изменения сопровождаются обновлением docs/progress/'
}

if ($hasRules -and -not $hasDecisions) {
    Write-Output '[WARN] RULE_WITHOUT_DECISION: изменены документы-правила без записи в docs/DECISIONS.md'
    $warn++
}

$secretPatterns = @('\.env$', '\.env\.', '\.pem$', '\.key$', '(^|/)id_rsa', 'credentials\.json$')
foreach ($path in $changed) {
    foreach ($pattern in $secretPatterns) {
        if ($path -match $pattern) {
            Write-Output ("[FAIL] SECRET_PATH: {0} — секреты не публикуются" -f $path)
            $fail++
            break
        }
    }
}

foreach ($path in $changed) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
    $size = (Get-Item -LiteralPath $path).Length
    $mb = [math]::Round($size / 1MB, 2)
    if ($size -gt 100MB) {
        Write-Output ("[FAIL] FILE_TOO_LARGE: {0} — {1} MB > 100 MB (лимит GitHub)" -f $path, $mb)
        $fail++
    }
    elseif ($size -gt 50MB) {
        Write-Output ("[WARN] LARGE_FILE: {0} — {1} MB > 50 MB (GitHub предупредит; нужен отчёт владельцу)" -f $path, $mb)
        $warn++
    }
}

if ($fail -gt 0) {
    Write-Output ("ИТОГ: FAIL (ошибок {0}, предупреждений {1})" -f $fail, $warn)
    exit 1
}

Write-Output ("ИТОГ: PASS (предупреждений {0})" -f $warn)
exit 0
