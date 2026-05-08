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

function Get-CleanList {
    param(
        [object[]]$Lines
    )

    $items = @()
    foreach ($line in $Lines) {
        $name = ($line -replace "`0", "").Trim()
        if ($name) {
            $items += $name
        }
    }

    return $items
}

function Get-DefaultWslDistro {
    $statusLines = wsl.exe --status 2>$null
    foreach ($line in $statusLines) {
        $cleanLine = ($line -replace "`0", "").Trim()
        if ($cleanLine -match '^Default Distribution:\s*(.+)$') {
            return $Matches[1].Trim()
        }
    }

    return $null
}

function Get-RtkWslDistroPreference {
    $userValue = [Environment]::GetEnvironmentVariable("RTK_WSL_DISTRO", "User")
    if (-not [string]::IsNullOrWhiteSpace($userValue)) {
        return $userValue.Trim()
    }

    if (-not [string]::IsNullOrWhiteSpace($env:RTK_WSL_DISTRO)) {
        return $env:RTK_WSL_DISTRO.Trim()
    }

    return $null
}

Write-Status "Checking Windows WSL availability"
$wslStatus = wsl.exe --status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "WSL is not available in this environment."
    $wslStatus | Out-String | Write-Host
    exit 1
}
Write-Status "WSL is installed."

$targetDistro = Get-RtkWslDistroPreference
if (-not $targetDistro) {
    $targetDistro = Get-DefaultWslDistro
}
if (-not $targetDistro) {
    $registeredDistros = Get-CleanList (wsl.exe -l -q 2>$null)
    if ($registeredDistros.Count -eq 1) {
        $targetDistro = $registeredDistros[0]
    }
}

if (-not $targetDistro) {
    Write-Status "No target distro could be determined for this Windows user."
    Write-Host "  Set RTK_WSL_DISTRO to the distro name and retry."
    exit 1
}

Write-Status "Target distro: $targetDistro"

$probe = wsl.exe -d "$targetDistro" -- /bin/true 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "Distro '$targetDistro' could not be started from this Windows user."
    if ($AutoFix) {
        Write-Status "AutoFix enabled: attempting 'wsl --install -d $targetDistro --no-launch'"
        wsl.exe --install -d $targetDistro --no-launch
        $probe = wsl.exe -d "$targetDistro" -- /bin/true 2>&1
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Status "Still unable to start '$targetDistro' from WSL."
    $probe | Out-String | Write-Host
    Write-Host "  If the distro exists but is not visible in this session, re-open the host shell or run scripts/rtk_pin_wsl.ps1 again."
    exit 1
}

Write-Status "Distro '$targetDistro' is reachable."

$rtkCommand = Get-Command rtk -ErrorAction SilentlyContinue
if (-not $rtkCommand) {
    Write-Status "rtk is not on PATH in Windows."
    exit 1
}
Write-Status ("Windows rtk path: " + $rtkCommand.Path)

$wslRtkPath = wsl.exe -d "$targetDistro" -- bash -lc "command -v rtk" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $wslRtkPath) {
    Write-Status "rtk is not installed inside WSL distro '$targetDistro'."
    Write-Host "  Install RTK in WSL, then retry."
    exit 1
}

$wslRtkVersion = wsl.exe -d "$targetDistro" -- rtk --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Status "rtk inside WSL failed to execute."
    exit 1
}

Write-Status ("WSL rtk path: " + (($wslRtkPath -replace "`0", "").Trim()))
Write-Status ("WSL rtk version: " + (($wslRtkVersion -replace "`0", "").Trim()))
Write-Status "RTK routing through WSL is healthy."
