param(
    [switch]$ClearProcessOnly
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param(
        [string]$Message
    )

    Write-Host "[rtk-unpin-wsl] $Message"
}

Write-Status "Clearing RTK_WSL_DISTRO from the current process."
Remove-Item Env:\RTK_WSL_DISTRO -ErrorAction SilentlyContinue

if ($ClearProcessOnly) {
    Write-Status "Process environment cleared."
    exit 0
}

Write-Status "Clearing RTK_WSL_DISTRO from the current user profile."
[Environment]::SetEnvironmentVariable("RTK_WSL_DISTRO", "", "User")

$persistedValue = [Environment]::GetEnvironmentVariable("RTK_WSL_DISTRO", "User")
if (-not [string]::IsNullOrWhiteSpace($persistedValue)) {
    throw "Failed to clear RTK_WSL_DISTRO for the current user."
}

Write-Status "User environment cleared."
