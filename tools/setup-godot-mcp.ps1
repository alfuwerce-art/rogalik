<#
.SYNOPSIS
    Recreate the local Godot MCP server used by the `rogalik-dev` preset.

.DESCRIPTION
    Clones @tugcantopaloglu/godot-mcp v3.1.0 (MIT) into tools/godot-mcp and
    builds build/index.js with the Node runtime and pnpm that ship inside
    DeepSeek Harness. No system-wide Node.js is required and nothing is
    installed into the DSH profile by this script.

    The repository excludes tools/godot-mcp from Git; run this script after a
    fresh clone, or whenever build/index.js is missing.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/setup-godot-mcp.ps1
#>
param(
    [string]$RepoUrl = 'https://github.com/tugcantopaloglu/godot-mcp.git',
    [string]$Tag = 'v3.1.0',
    [string]$DshRoot = 'C:\Users\bow\AppData\Local\Programs\DeepSeek Harness'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root 'tools\godot-mcp'
$nodeExe = Join-Path $DshRoot 'DeepSeek Harness.exe'
$pnpmCli = Join-Path $DshRoot 'resources\runtime\primary-runtime\dependencies\pnpm\bin\pnpm.cjs'
$storeDir = Join-Path $root '.cache\pnpm-store'

if (-not (Test-Path -LiteralPath $nodeExe)) { throw "Bundled Node runtime not found: $nodeExe" }
if (-not (Test-Path -LiteralPath $pnpmCli)) { throw "Bundled pnpm not found: $pnpmCli" }

if (-not (Test-Path -LiteralPath (Join-Path $target '.git'))) {
    Write-Host "Cloning $RepoUrl at $Tag ..."
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    # Windows schannel cannot always acquire credentials in restricted shells;
    # the OpenSSL backend of Git for Windows works without a certificate store.
    git -c http.sslBackend=openssl clone --depth 1 --branch $Tag $RepoUrl $target
    if ($LASTEXITCODE -ne 0) { throw 'git clone failed' }
} else {
    Write-Host "Using existing checkout: $target"
}

Push-Location $target
try {
    Write-Host 'Installing dependencies (no lifecycle scripts) ...'
    & $nodeExe $pnpmCli install --ignore-scripts --node-linker=hoisted --store-dir $storeDir
    if ($LASTEXITCODE -ne 0) { throw 'pnpm install failed' }

    Write-Host 'Compiling TypeScript ...'
    & $nodeExe (Join-Path $target 'node_modules\typescript\bin\tsc')
    if ($LASTEXITCODE -ne 0) { throw 'tsc failed' }

    Write-Host 'Copying GDScript helpers into build/ ...'
    & $nodeExe (Join-Path $target 'scripts\build.js')
    if ($LASTEXITCODE -ne 0) { throw 'build script failed' }
} finally {
    Pop-Location
}

$entry = Join-Path $target 'build\index.js'
if (-not (Test-Path -LiteralPath $entry)) { throw "Build did not produce $entry" }

Write-Host ''
Write-Host "Ready: $entry"
Write-Host 'Verify it with:'
Write-Host '  powershell -NoProfile -ExecutionPolicy Bypass -File tools\godot-mcp\probe-mcp.ps1'
