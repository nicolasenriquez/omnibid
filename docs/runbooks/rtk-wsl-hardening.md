# RTK Windows WSL Hardening Runbook

Use this runbook when RTK on Windows keeps falling back to the local proxy shim because it cannot resolve the WSL target consistently across sessions.

## Scope

- Windows user-level RTK setup.
- Persistent WSL target pinning for RTK.
- Safe diagnosis and reversible cleanup.
- No repository runtime changes beyond the documented helper scripts and `justfile` surface.

## Why this exists

RTK official docs recommend WSL for the full hook experience on Windows. Native Windows works, but the hook path is limited and session-dependent. This runbook gives a durable, explicit setup so the same WSL target is used across new sessions.

## Canonical Commands

- Diagnose current state:
  - `just rtk-doctor`
- Persist the WSL preference for the current user:
  - `just rtk-pin-wsl -- -Distro Ubuntu`
- Persist the WSL preference and attempt to set the WSL default:
  - `just rtk-pin-wsl -- -Distro Ubuntu -SetWslDefault`
- Revert the persistent preference:
  - `just rtk-unpin-wsl`
- Clear only the current process:
  - `just rtk-unpin-wsl -- -ClearProcessOnly`

When `rtk` is available for agent-issued commands, use the RTK-prefixed equivalents:

- `rtk just rtk-doctor`
- `rtk just rtk-pin-wsl -- -Distro Ubuntu`
- `rtk just rtk-unpin-wsl`

## Setup Flow

1. Confirm the target distro name you want RTK to use.
2. Run `just rtk-doctor`.
3. If the distro preference is missing, run `just rtk-pin-wsl -- -Distro Ubuntu`.
4. If the distro is visible in the current session and you want WSL to prefer it globally, rerun with `-SetWslDefault`.
5. Open a fresh Windows session and rerun `just rtk-doctor`.

## Safety Rules

- The pin helper only writes the user-level `RTK_WSL_DISTRO` value and the current process value.
- The optional `-SetWslDefault` path first probes the distro with `wsl.exe --distribution <name> -- /bin/true` before changing the default.
- If the probe fails, the default is not changed.
- Cleanup is reversible through `just rtk-unpin-wsl`.

## Failure Modes

- `rtk-doctor` reports no target distro:
  - The user-level preference is missing and WSL has no usable default for RTK.
- `rtk-doctor` reports the distro cannot be started:
  - The current Windows session cannot see or start that distro.
  - Open a fresh session and retry before changing anything else.
- `rtk --version` still falls back to the proxy shim:
  - The Windows host still cannot resolve WSL for the active session.
  - Re-check `just rtk-doctor`.

## Cleanup

Use cleanup only when you want to remove the pinned preference:

1. `just rtk-unpin-wsl`
2. Open a fresh Windows session
3. Re-run `just rtk-doctor` if you want to confirm the state was cleared

## Related Files

- [`justfile`](../../justfile)
- [`scripts/rtk_doctor.ps1`](../../scripts/rtk_doctor.ps1)
- [`scripts/rtk_pin_wsl.ps1`](../../scripts/rtk_pin_wsl.ps1)
- [`scripts/rtk_unpin_wsl.ps1`](../../scripts/rtk_unpin_wsl.ps1)
- Codex instruction file: `.codex/RTK.md`
