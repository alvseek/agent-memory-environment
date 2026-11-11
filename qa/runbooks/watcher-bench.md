# Watcher bench — QA runbook

## Goal

Operate the isolated probe rig and distinguish its own health from actual watcher or battery verification.

## Preconditions

Windows and Python 3.12+; see the [configuration inventory](../config/REQUIRED.md). No Joro watcher, API credential, client process or background service is required for the rig's current self-smoke.

## Reset → Clean State

Use the RESET mechanism in the [R/I/A/O index](../README.md#the-riao-loop). It clears only this checkout's marked QA sandbox, after validating any recorded child process by PID and creation time. It refuses unknown files, marker mismatches and links instead of cleaning broadly.

## Inject → Realistic Data

Use the INJECT mechanism in the [index](../README.md#the-riao-loop). Its dummy seed is a synthetic bench specimen, not a fidelity-checked Claude/OpenCode flow fixture.

## Daily Loop / Quick Start

Run the four commands in the [Daily Loop](../README.md#daily-loop) in order. ACT supervises a real finite Python child; OBSERVE validates this run's readiness/result identity and confirms that child exited. A successful result explicitly says `watcher_verified: false` and `battery_verified: false`.

## Act → Exercise the System

## Config Switching

The committed configuration is QA-only. Runtime files are created outside Git in a Windows-resolved temporary namespace; no global settings are copied or rewritten. Future client/native tests must preserve that isolation and declare any real-host side effect before running.

## Troubleshooting

| Symptom | Meaning / action |
|---|---|
| Expected completed phase | Run the index commands in order; RESET intentionally invalidates earlier evidence. |
| Missing/stale result | OBSERVE correctly refuses to call the rig healthy. Inspect sandbox logs, then reset and repeat. |
| Unexpected or linked file | Inspect it; do not weaken the guard or point RESET at another directory. |
| Sandbox busy | Another command owns the mutex; wait for that exact run to finish. |
| Cannot query child ownership | Stop and inspect permissions; do not treat access denied as process death. |

## Known Gotchas

This is a finite-probe rig, not an always-running application stack. A bench smoke is not an agent or battery test. Battery/locked-screen tests and their cleanup evidence remain pending, and must be coordinated with Alvi rather than triggered by these default commands.
