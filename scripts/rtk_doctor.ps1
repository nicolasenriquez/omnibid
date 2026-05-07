param(
    [switch]$AutoFix
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param(
        [string]$Message
    )
    Write-Host "[rtk-doctor] $Message"
}

Write-Status "Checking Windows WSL availability"
$wslStatus = wsl.exe --status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "WSL is not available in this environment."
    $wslStatus | Out-String | Write-Host
    exit 1
}
Write-Status "WSL is installed."

$targetDistro = if ($env:RTK_WSL_DISTRO) { $env:RTK_WSL_DISTRO } else { "Ubuntu" }
Write-Status "Target distro: $targetDistro"

$distrosRaw = wsl.exe -l -q 2>$null
$distros = @()
foreach ($line in $distrosRaw) {
    $name = ($line -replace "`0", "").Trim()
    if ($name) {
        $distros += $name
    }
}

if (-not ($distros -contains $targetDistro)) {
    Write-Status "Distro '$targetDistro' is not registered."
    if ($AutoFix) {
        Write-Status "AutoFix enabled: attempting 'wsl --install -d $targetDistro --no-launch'"
        wsl.exe --install -d $targetDistro --no-launch
        $distrosRaw = wsl.exe -l -q 2>$null
        $distros = @()
        foreach ($line in $distrosRaw) {
            $name = ($line -replace "`0", "").Trim()
            if ($name) {
                $distros += $name
            }
        }
    }
}

if (-not ($distros -contains $targetDistro)) {
    Write-Status "Still missing '$targetDistro'. Install it with:"
    Write-Host "  wsl --install -d $targetDistro --no-launch"
    exit 1
}

Write-Status "Distro '$targetDistro' is registered."

$rtkCommand = Get-Command rtk -ErrorAction SilentlyContinue
if (-not $rtkCommand) {
    Write-Status "rtk is not on PATH in Windows."
    exit 1
}
Write-Status ("Windows rtk path: " + $rtkCommand.Path)

$wslRtkPath = wsl.exe -d $targetDistro -- bash -lc "command -v rtk" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $wslRtkPath) {
    Write-Status "rtk is not installed inside WSL distro '$targetDistro'."
    Write-Host "  Install RTK in WSL, then retry."
    exit 1
}

$wslRtkVersion = wsl.exe -d $targetDistro -- rtk --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Status "rtk inside WSL failed to execute."
    exit 1
}

Write-Status ("WSL rtk path: " + (($wslRtkPath -replace "`0", "").Trim()))
Write-Status ("WSL rtk version: " + (($wslRtkVersion -replace "`0", "").Trim()))
Write-Status "RTK routing through WSL is healthy."
