param(
    [string]$Distro = "Ubuntu",
    [switch]$SetWslDefault
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param(
        [string]$Message
    )

    Write-Host "[rtk-pin-wsl] $Message"
}

if ([string]::IsNullOrWhiteSpace($Distro)) {
    throw "Distro name is required."
}

$cleanDistro = $Distro.Trim()

Write-Status "Persisting RTK_WSL_DISTRO='$cleanDistro' in the user environment."
[Environment]::SetEnvironmentVariable("RTK_WSL_DISTRO", $cleanDistro, "User")
[Environment]::SetEnvironmentVariable("RTK_WSL_DISTRO", $cleanDistro, "Process")

$persistedValue = [Environment]::GetEnvironmentVariable("RTK_WSL_DISTRO", "User")
if ($persistedValue -ne $cleanDistro) {
    throw "Failed to persist RTK_WSL_DISTRO for the current user."
}

Write-Status "User environment updated."

if ($SetWslDefault) {
    Write-Status "Verifying that '$cleanDistro' can start before changing the default."
    & wsl.exe --distribution "$cleanDistro" -- /bin/true
    if ($LASTEXITCODE -ne 0) {
        Write-Status "WSL cannot start '$cleanDistro' from this session, so the default was not changed."
        exit $LASTEXITCODE
    }

    Write-Status "Attempting to set WSL default distro to '$cleanDistro'."
    & wsl.exe --set-default "$cleanDistro"
    if ($LASTEXITCODE -ne 0) {
        Write-Status "WSL default could not be updated from this environment."
        exit $LASTEXITCODE
    }

    Write-Status "WSL default updated."
}
