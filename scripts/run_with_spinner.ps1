[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [Parameter(Mandatory = $true)]
    [string]$CommandText
)

$ErrorActionPreference = "Stop"

function Invoke-CommandText {
    param([Parameter(Mandatory = $true)][string]$Text)
    $script = [scriptblock]::Create($Text)
    & $script
    if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$spinnerPath = Join-Path $PSScriptRoot "terminal_spinner.ps1"
if (-not (Test-Path -LiteralPath $spinnerPath)) {
    throw "Spinner script not found: $spinnerPath"
}

$pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
if ($null -eq $pwsh) {
    . $spinnerPath
    $localScript = [scriptblock]::Create($CommandText)
    Start-TerminalSpinner -Message $Message -ScriptBlock $localScript
    if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    exit 0
}

$spinnerPathEscaped = $spinnerPath.Replace("'", "''")
$messageEscaped = $Message.Replace("'", "''")
$pwdEscaped = ((Get-Location).Path).Replace("'", "''")
$runnerScript = @"
`$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath '$pwdEscaped'
. '$spinnerPathEscaped'
Start-TerminalSpinner -Message '$messageEscaped' -ScriptBlock { $CommandText }
"@

& $pwsh.Source -NoProfile -NonInteractive -Command $runnerScript
if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
