# Pipeline Locking Specification

## ADDED Requirements

### Requirement: The system MUST use scoped advisory locks to prevent concurrent duplicate execution
The system SHALL acquire a `pg_try_advisory_lock` scoped to the logical unit of work before executing any Mercado Publico sync operation, and SHALL release it when the operation completes or fails.

#### Scenario: Two identical syncs are started concurrently
- **WHEN** two processes attempt to run the same Mercado Publico sync (same mode, same date window, same business key) at the same time
- **THEN** only one process acquires the advisory lock and proceeds
- **AND** the second process fast-fails with a clear lock-contention message.

#### Scenario: Two different syncs are started concurrently
- **WHEN** process A runs `active-discovery` for today and process B runs `detail-by-codigo` for a different notice code
- **THEN** both processes acquire their respective scoped locks without contention
- **AND** both execute concurrently.

### Requirement: Lock keys MUST be deterministic and scoped
The system SHALL derive lock keys from the provider, mode, and business-unit identifiers (date, window, external code) so that locks are repeatable and do not collide across unrelated work units.

#### Scenario: Lock key is computed for a rolling-window sync
- **WHEN** a rolling-window sync is started for date `2026-05-10` and window `4d`
- **THEN** the lock key is `mercado_publico:rolling_window:2026-05-10:4d`
- **AND** any other sync with the same key contends on the same lock.

### Requirement: Lock acquisition and release MUST be logged
The system SHALL emit structured log events when an advisory lock is acquired and when it is released, including the lock key and `pipeline_run_id`.

#### Scenario: An operator investigates a lock-contention failure
- **WHEN** the operator inspects the log output for a failed sync
- **THEN** they can see which lock key was contended and which `pipeline_run_id` currently holds it
- **AND** no secrets are included in the lock-key log.
