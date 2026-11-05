$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot '.local-build/web'
$target = Join-Path $repoRoot 'backend/web'
$required = @('index.html', 'index.js', 'index.pck', 'index.wasm')
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $name))) {
        throw "Missing $name. Export the Godot Web preset first."
    }
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
# Only copy exported runtime assets, never credentials or the project directory.
Get-ChildItem -LiteralPath $source -File | Where-Object {
    $_.Name -match '^index(?:\.[a-z-]+)*\.(html|js|pck|wasm|png)$'
} | ForEach-Object {
    if ($_.Length -ge 100MB) { throw "Asset exceeds GitHub's single-file limit: $($_.Name)" }
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $target $_.Name) -Force
}
Write-Host 'Staged browser game in backend/web. Commit and deploy these assets with the backend.'
