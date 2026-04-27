function Start-TerminalSpinner {
    [CmdletBinding()]
    param(
        [string]$Message = "Working",
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock
    )

    if ($PSVersionTable.PSVersion.Major -lt 5) {
        throw "Start-TerminalSpinner requires PowerShell 5+."
    }

    # Single-frame braille spinner sequence.
    $sequence = @("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    $intervalMs = 100
    $index = 0
    $workingDirectory = (Get-Location).Path
    $cursorHidden = $false

    $scriptText = $ScriptBlock.ToString()

    $job = Start-Job -ScriptBlock {
        param(
            [string]$InnerScriptText,
            [string]$InnerWorkingDirectory
        )
        $ErrorActionPreference = "Continue"
        if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
            $PSNativeCommandUseErrorActionPreference = $false
        }
        Set-Location -LiteralPath $InnerWorkingDirectory
        $inner = [scriptblock]::Create($InnerScriptText)
        & $inner 2>&1 | ForEach-Object { Write-Output ($_.ToString()) }
        if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
            throw "ScriptBlock exited with code $LASTEXITCODE."
        }
    } -ArgumentList $scriptText, $workingDirectory

    function Clear-SpinnerLine {
        $width = 120
        try {
            $width = [Math]::Max(16, [Console]::BufferWidth - 1)
        } catch {
            $width = 120
        }
        Write-Host ("`r" + (" " * $width) + "`r") -NoNewline
    }

    try {
        try {
            [Console]::CursorVisible = $false
            $cursorHidden = $true
        } catch {
            $cursorHidden = $false
        }

        while ($job.State -eq "Running" -or $job.State -eq "NotStarted") {
            $frame = $sequence[$index % $sequence.Count]
            Write-Host ("`r$frame`t$Message") -NoNewline
            Start-Sleep -Milliseconds $intervalMs
            $index++
        }

        Clear-SpinnerLine

        if ($job.State -eq "Failed") {
            $jobError = $job.ChildJobs[0].Error | Select-Object -Last 1
            if ($null -ne $jobError) {
                throw $jobError
            }
            $reason = $job.ChildJobs[0].JobStateInfo.Reason
            if ($null -ne $reason) {
                throw $reason
            }
            throw "ScriptBlock failed."
        }

        Receive-Job -Job $job | Write-Output
    } catch {
        Clear-SpinnerLine
        throw
    } finally {
        if ($null -ne $job) {
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        }
        if ($cursorHidden) {
            try {
                [Console]::CursorVisible = $true
            } catch {
            }
        }
    }
}

# Usage example:
# Start-TerminalSpinner -Message "Processing" -ScriptBlock { Start-Sleep -Seconds 3 }
