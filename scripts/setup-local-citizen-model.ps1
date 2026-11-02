param([string]$Installer = "$env:TEMP\Aitizen-OllamaSetup.exe", [switch]$ModelOnly)
$ErrorActionPreference = 'Stop'
$statusFile = Join-Path $PSScriptRoot '..\backend\local-model-setup.status'
function Report([string]$Message) {
    Set-Content -LiteralPath $statusFile -Value "$(Get-Date -Format o) $Message"
}
try {
    if (-not $ModelOnly) {
    Report 'DOWNLOADING official Ollama installer (resumable)'
    if (-not (Test-Path -LiteralPath $Installer) -or (Get-Item -LiteralPath $Installer).Length -ne 1580352416) {
        & curl.exe --silent --show-error --location --fail --retry 3 -C - -o $Installer 'https://github.com/ollama/ollama/releases/download/v0.35.1/OllamaSetup.exe'
        if ($LASTEXITCODE -ne 0) { throw 'Installer download failed; rerun to resume.' }
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $Installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Ollama') {
        throw 'Installer signature is invalid or the signer is not Ollama. Nothing installed.'
    }
    Report 'INSTALLING verified Ollama installer'
    $installation = Start-Process -FilePath $Installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -WindowStyle Hidden -PassThru
    $installation.WaitForExit()
    if ($installation.ExitCode -ne 0) { throw "Installer returned $($installation.ExitCode)" }
    }
    $ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (-not (Test-Path -LiteralPath $ollamaExe)) { throw 'Ollama executable not found after installation.' }
    try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 3 }
    catch {
        Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden
        Start-Sleep -Seconds 5
    }
    Report 'DOWNLOADING qwen2.5:1.5b local model (about 986 MB)'
    & $ollamaExe pull 'qwen2.5:1.5b'
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed; rerun ollama pull qwen2.5:1.5b.' }
    Report 'TESTING local structured decision'
    $body = @{
        model = 'qwen2.5:1.5b'; stream = $false
        options = @{ temperature = 0; num_ctx = 2048; num_predict = 100 }
        format = @{ type='object'; properties=@{goal=@{type='string';enum=@('EAT','BUILD')};rationale=@{type='string'}};required=@('goal','rationale');additionalProperties=$false }
        messages = @(@{role='user';content='A citizen is very hungry and has food in inventory. Choose EAT or BUILD and give a short rationale.'})
    } | ConvertTo-Json -Depth 8
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-RestMethod 'http://127.0.0.1:11434/api/chat' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 180
    $proposal = $result.message.content | ConvertFrom-Json
    if ($proposal.goal -ne 'EAT' -or -not $proposal.rationale) { throw 'Model failed the structured survival decision check.' }
    Report "READY qwen2.5:1.5b installed; local JSON decision passed in $([math]::Round($timer.Elapsed.TotalSeconds,1)) seconds. Citizen pilot remains disabled pending latency integration check."
} catch {
    Report "FAILED $($_.Exception.Message)"
    exit 1
}
