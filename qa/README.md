---
doc_type: qa-riao-readme
---

# Joro — QA Instrument

This is the earlier exploratory Windows rig, retained after the watcher was simplified. Its specimen proves the rig's process/config/result wiring only. Use the [project README](../README.md) and [current watcher plan](../plans/2026-11-11-joro-host-agent-setup/SP-1-agent-keep-awake.md) for product status and focused tests; this bench is not required to install or operate Joro. Battery protection remains unverified.

## The R/I/A/O Loop

| Phase | What it means in Joro | Mechanism | Status |
|---|---|---|---|
| RESET | Validate the marked sandbox, stop only its verified owned child if needed, and recreate a clean run. Never recursively delete arbitrary paths or touch real client settings. | [bench.py](scripts/bench.py) — `reset` | documented — self-smoke passed |
| INJECT | Load the deterministic synthetic baseline and this run's identity. Seed strategy: dummy. | [bench.py](scripts/bench.py) — `inject`; [source](seeds/baseline.json) | documented — self-smoke passed |
| ACT | Supervise the finite `bench-self-smoke` child; capture its output and exit. No arbitrary command/probe selection is exposed yet. | [bench.py](scripts/bench.py) — `act` | documented — self-smoke passed |
| OBSERVE | Check readiness/result/run/process identities, successful exit and cleanup; reject stale, missing or failing evidence. | [bench.py](scripts/bench.py) — `observe` | documented — healthy and broken controls passed |

These links are the loop resolver. Each points to the shared executable with a distinct phase argument, not a naming convention or an in-script category marker.

## First-Time Setup

1. On Windows, open a terminal in this repository and verify `python --version` reports 3.12 or later. No pip packages are required.
2. Read the [configuration inventory](config/REQUIRED.md). The sandbox is fixed under Windows Local AppData: `Temp/opencode/joro-qa/<checkout-id>/<sandbox-name>`; paths cannot be supplied as names.
3. Run the Daily Loop. OBSERVE should report `ok: true`, `child_exited: true`, `watcher_verified: false`, and `battery_verified: false`.
4. Run the guard/regression tests:

```powershell
python -m unittest discover -s qa/scripts -p test_bench.py -v
```

The native power-request boundary also has explicit tests. Running the following briefly acquires real system/execution keep-awake requests (two seconds), then releases them; it does not change power settings, hold the display or lock/sleep the PC:

```powershell
python -m unittest discover -s qa/scripts -p test_power_requests.py -v
```

Request-count and failure-path unit tests use a doubled Windows API:

```powershell
python -m unittest discover -s qa/scripts -p test_power_state.py -v
```

These native integration tests construct their own handles; no upstream-state fixture is needed. Handle cleanup was mutation-tested by omitting the close, observing the expected failure, restoring it and rerunning green. They do not prove sustained sleep prevention or battery/locked-screen behavior.

The coordinated host observation has a read-only preflight:

```powershell
python qa/scripts/battery_endurance_probe.py
```

Only after agreeing with the operator, add `--coordinated` to arm the test. It waits up to ten minutes for DC power plus a locked physical console, then samples for 960 seconds with system/execution requests only. It never locks the machine, requests a display hold or changes sleep settings. Sleep timeout must still match the agreed 600 seconds; otherwise it refuses and requires re-planning. Runtime samples and results stay in a fresh external endurance directory. It aborts on a power/lock/console change or OS critical-battery flag and releases its handles. A passing observation does not exclude other inhibitors or prove client/watcher correctness.

## Daily Loop

From the repository root:

```powershell
python qa/scripts/bench.py reset
python qa/scripts/bench.py inject
python qa/scripts/bench.py act
python qa/scripts/bench.py observe
```

Each command must succeed before the next starts. OBSERVE exits nonzero on an invalid run. It is safe as a standalone read after a completed ACT; before ACT it intentionally reports that no valid completed run exists.

Runtime stdout/stderr and evidence remain in that run's guarded sandbox for inspection until RESET. Unit tests use separate generated `test-<12 hex digits>` sandboxes and remove only their own exact files. Nothing is written to live Joro/client state or to Windows power settings.

## Where Everything Lives

| Material | Location | Owner |
|---|---|---|
| Loop executable and rig regression tests | [scripts/](scripts/) | /build-qa-bench |
| Required inputs and isolation rules | [config/REQUIRED.md](config/REQUIRED.md) | /build-qa-bench |
| Synthetic baseline source | [seeds/baseline.json](seeds/baseline.json) | /build-qa-bench |
| Operating instructions | [watcher-bench runbook](runbooks/watcher-bench.md) | /build-qa-bench |
| Discoverability audit | [qa-map.md](qa-map.md) | /map-qa-instrument |

The [tray/log checklist](checklists/tray-and-logs.md) records feature-specific visual and lifecycle checks separately from the finite rig. Focused tests live in the `joro-awake` submodule; run `python -m unittest discover -s joro-awake/tests -p "test_keep_awake*.py" -v`. Its filesystem integration tests create preconditions through the real logger/helper writer, double process identity/native locking, and own temporary-directory teardown; no upstream fixture is needed. Rotation and active-state interpretation were mutation-tested red then restored green on 2026-11-14. A separate disposable smoke exercised four real concurrent log writers and installed CLI start/stop/exit; its evidence and limits are in the [tray plan](../plans/2026-11-14-tray-and-logs.md). Native menu callbacks, future sign-in startup, and visible icon rendering are not proven by those checks.

## Config Switching

The committed config is the QA baseline, not a production target. There is no local/production toggle: the rig resolves a fixed, marked temporary namespace through Windows and accepts only constrained sandbox names. Credentials and real user settings are neither needed nor copied. New native/client probes must explicitly declare their boundary and opt-in side effects before joining the rig.

## Known Gaps / Debts

- The bench's default ACT executes only its own fixed specimen. The separate [native request tests](scripts/test_power_requests.py) exercise real Windows handles; they are not selected automatically by ACT. The [disposable Claude experiment](scripts/claude_lifecycle_probe.py) now measured allowed and denied tool calls after the earlier quota refusal. It found a missing classic-hook approval/resume signal on the print/SDK path, so the planned wait-release behavior needs a new decision. Interactive-terminal parity, sustained host-power and full watcher verification remain pending.
- Battery/locked-screen and client lifecycle feasibility are unproven. The coordinated host observer exists and its preflight works; its endurance result is pending. The watcher plan owns these checks, including Alvi's coordination and the stop-on-failure gate.
- Per-stage fixtures/integration tests belong to `/integration-test`; the tray/log filesystem boundary is covered without an upstream fixture. Native concurrent logging has separate smoke evidence; visible desktop lifecycle still needs the checklist.
- Per-feature checklists belong to `/generate-qa-checklist`; the tray/log checklist exists but is not signed off. This document and the unit suite are not a completed watcher checklist.
- Tested host/runtime evidence is recorded in the watcher plan. No claim is made that this Windows-only rig runs on other platforms.

## Where To Go Next

- Operate the rig using the [runbook](runbooks/watcher-bench.md).
- Inspect the [QA map](qa-map.md) for current material and gaps.
- Continue the [watcher feasibility plan](../plans/2026-11-11-joro-host-agent-setup/SP-1-agent-keep-awake.md); add and run real boundary tests through `/integration-test` as those probes become available.
- Use `/run-qa-test` for repeatable runtime verification. A successful rig self-smoke is not a successful watcher/battery run.
