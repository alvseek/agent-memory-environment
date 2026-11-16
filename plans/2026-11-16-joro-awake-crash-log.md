# Quick Wizard Plan: Joro Awake crash log

## Plan State
- **Source Protocol**: `/quick-wizard`
- **Approval**: APPROVED
- **Confirmation**: Alvi, 2026-11-16: "approved. use sonnet 5.5, no specific rules. please download the latest version then"
- **Execution split**: steps 1–4 are dispatched to an anonymous worker on Sonnet 5.5 through Einherjar; steps 5–6 stay with the supervising software-architect session, which also runs the quality review and QA handoff.

To resume: load the source protocol and this entire plan, inspect approval and the Execution Log, and continue with the next unfinished step only when its gates are cleared.

## Inherited Context

**From the parent plan**
- **Parent plan**: None — not a sub-plan
- **Assigned scope**: None
- **Inherited decisions**: None
- **Contracts / pushed-down items**: None

**From pre-planning discussion**
- **Discussion**: Pre-planning discussion, 2026-11-16
- **Agreed scope**: Joro Awake has ended several times with nothing recorded. It needs a rolling log that says what happened when a crash happens, the kind a marketed app would have. (Settled)
- **Settled decisions**:
  - The record is the deliverable, not recovery: nothing restarts a dead helper or tray automatically. (Settled — "we need to have proper rolling log so we know what happened when crash happen")
  - Reported symptom: the tray icon was gone. (Settled — his observation)
  - `~/.joro` was recreated on 2026-11-16 at 10:33 by his reinstall, so no earlier log exists on this machine. (Settled — his statement)
- **Considered and rejected**: None

## Objective
Make every way the helper or tray can end leave a line that says when it ended and how, so the next silent disappearance can be diagnosed from `~/.joro` alone.

## Specification
- **Required behavior**:
  - Every recorded error carries its exception type and traceback, not only its message.
  - An exception that escapes a thread or the top level is recorded before the process ends.
  - A native fault (a crash below Python, inside a Windows call) leaves a Python stack dump in `~/.joro/crash-helper.log` or `~/.joro/crash-tray.log`.
  - When a helper or tray starts and finds the state file of a previous run whose process is dead, it records that the previous run ended without a stop, with that run's PID and last heartbeat time.
  - The helper records the tray's exit code when the tray process ends; the tray records the helper's exit code when the helper process ends. The line names the code in hex and its common meaning (clean exit, killed, access violation, logoff or shutdown).
  - The helper records a stall when the gap between two loop ticks exceeds ten seconds, with the gap length. Ten seconds is the staleness limit the tray already applies to the helper's heartbeat.
  - Start lines carry the Joro version and Python version; the helper's stop line says whether it was requested or followed an error.
- **Constraints**:
  - `keep-awake.log` keeps its bound: the current file plus four backups, 1 MiB each, written under the existing named mutex.
  - The two fault files are bounded too: each is cut back at process start once it passes 256 KiB.
  - A logging or diagnostic failure never releases a power request and never ends the helper or tray.
  - Entries never contain prompts, tool contents or credentials. Hook and event failures record the exception type and stack frames only, never the exception message. Tracebacks do contain local file paths.
  - An oversized entry keeps its event name and the end of its traceback instead of being replaced by a bare "truncated" marker.
  - No new source file, so the installer's and the package builder's file lists stay as they are.
- **Out of scope**: automatic restart of a dead helper or tray; detecting Windows sleep, resume, logoff or shutdown directly; shipping logs anywhere; a GitHub release.

## Confirmed Decisions

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | Where this ships | Commit and push `joro-awake` and the parent, bump to 0.1.1, install and restart on this machine, no GitHub release yet | Confirmed by Alvi ("proceed"). The log is unproven until it catches a real crash, and a release is the step that is awkward to take back. |
| 2 | How much the log covers | Tracebacks, the ended-without-a-stop line, mutual exit codes, stall lines, and the native-fault files | Confirmed by Alvi ("proceed"). The exit code is the only thing that separates a kill from a crash. |
| 3 | Plan is saved | This file, beside the earlier Joro plans | Earlier Joro changes were tracked the same way. |
| 4 | Native faults go to their own files | `crash-helper.log`, `crash-tray.log` via `faulthandler.enable(file=...)` | The fault handler writes to a raw file handle during a crash and cannot take the log mutex or rotate. One file per process names the source. |
| 5 | Exit-code watch mechanism | Each process opens a handle to the other's PID (checked against its recorded creation time), polls it on its existing one-second tick, and reads `GetExitCodeProcess` once it is signalled | A handle opened while the process lives is the only way to read its exit code afterwards. No new thread or timer. |
| 6 | Ended-without-a-stop detection | Read the leftover `helper.json` / `tray.json` at start, before it is replaced | A clean stop deletes the file, so a leftover file whose process is dead is exact evidence, and `helper.json` already carries the last heartbeat. `tray.json` gains the same heartbeat field. |
| 7 | Stall threshold | Ten seconds between loop ticks | Reuses the limit the tray already applies, instead of a second number. |
| 8 | Hook and event privacy | Type and stack frames, no message | Keeps the existing rule that publisher errors record no content. |
| 9 | Product flow, integration | No decision | Nothing the user does changes, and no file list changes. |

## Success Criteria
- [ ] A helper killed with `taskkill /F` leaves a tray line naming its exit code, and the next start records that the previous run ended without a stop.
- [ ] A tray killed the same way leaves a helper line naming its exit code.
- [ ] A raised exception in the helper loop is recorded with type and traceback.
- [ ] Existing 31 tests still pass, and the log bound still holds.
- [ ] Unit tests written and passing for every step with testable logic (or the step says why it has none)
- [ ] Static quality review completed (Step 7 — delegated to `/analyze-code-quality`)
- [ ] QA Handoff completed (Step 8 — checklist built, or auto-skipped with reason recorded)

## Execution Steps
1. **Log module**: in `joro-awake/scripts/windows/joro_watcher/event_log.py`, add traceback-carrying error fields, tail-keeping truncation, the uncaught-exception hooks, the bounded fault-file setup, and the exit-code naming table → unit tests for each, including the size bound and the hook-privacy rule.
2. **Helper**: in `joro-awake/scripts/windows/keep_awake.py`, record the ended-without-a-stop line, watch the tray's process handle, record stalls, add version and stop reason, and pass tracebacks from `main()` → unit tests with a real child process for the exit code and a leftover state file for the unclean line.
3. **Tray**: in `joro-awake/scripts/windows/joro_watcher/tray.py`, watch the helper's process handle, write a heartbeat into `tray.json`, record its own ended-without-a-stop line → unit tests on the same pattern.
4. **Docs and version**: rewrite the Log section of `joro-awake/README.md` and the event-log row in the parent `README.md`, update `joro-awake/procedures/keep-awake.md` where it describes the log, set `VERSION` to 0.1.1 → full test run in both repos, including the parent's package test.
5. **Install and prove on this machine**: install, `exit`, `start`; then kill the helper and the tray in turn with `taskkill /F` and read the resulting lines; confirm `power_requested` and the Run key are as before → the three runtime success criteria above, observed in `~/.joro`.
6. **Commit and push**: commit `joro-awake`, push; move the parent's gitlink, commit, push; read both refs back from the remote → remote refs match local.

## Execution Log
**Execution Protocol for AI**: Load this entire plan at the start and after compaction. Check approval and pending STOP gates, then read the next unfinished execution step. Implement in order, verify its success criteria, and update its entry below before moving on. This file is the only execution tracker; do not use TodoWrite or a second log. Record actual results, not intentions.

- [x] **Step 1: Log module**
  - **Implementation**: `event_log.py` gained `failure()` (type + stack frames, message only on request), `describe_exit()` (hex code and meaning table), `timestamp()`, tail-keeping `_fit()` (oversized entries keep the event name, trimmed fields and the end of the traceback), `install_hooks()` (sys and threading excepthooks, chaining to the previous hooks) and `enable_fault_log()` (per-process `crash-<name>.log`, cut to its last 128 KiB at start when over 256 KiB, `faulthandler.enable` on the open handle, failures reported not raised). New `tests/test_keep_awake_event_log.py` (12 tests when step 1 ended; 13 after step 3 added the unusable-timestamp test).
  - **Verification / result**: `python -m unittest discover -s joro-awake/tests -p "test_keep_awake*.py"` → 43 tests, OK (31 existing + 12 new, as run at the end of step 1). Includes a real child process that segfaults via `ctypes.string_at(0)` and leaves a "Windows fatal exception" dump in the temp `crash-helper.log`, and a 600-entry run proving the log stays within five files of at most 1 MiB.
  - **Blockers / agreed deferrals**: none

- [x] **Step 2: Helper**
  - **Implementation**: `keep_awake.py`: `GetExitCodeProcess` binding; `created()` split out of `birth()`; `watch()` (handle opened and checked against the recorded creation time); `Peer` (attaches from a state file, polled on the helper's existing tick, records `peer_exited` with the hex code and meaning once, one attach attempt per process identity, failures recorded as type and frames only); `ended_without_stop()` (leftover `helper.json` of a dead process → `previous_run_ended_without_stop` with PID and last heartbeat, before the file is replaced); `version()`; stall record when two loop ticks are more than `STALL_LIMIT` (10 s) apart, on an injectable `CLOCK`; start line carries `version` and `python`; stop line moved into the final `finally` with `reason` `requested` or `error`; `main()` installs the exception hooks and fault file for `run` and `tray` and passes tracebacks (`failure()`) for errors, message-free for hook/event failures; `tray_start_failed` also carries the traceback. New `tests/test_keep_awake_lifecycle.py` (14 tests).
  - **Verification / result**: `python -m unittest discover -s joro-awake/tests -p "test_keep_awake*.py"` → 57 tests, OK (31 existing + 12 step 1 + 14 new, as run at the end of step 2). Real child processes: exit code 3 recorded as `0x00000003`, a killed child as `0x00000001` (taskkill meaning), a dead PID's leftover `helper.json` recorded as unclean with its PID and heartbeat, and a live process / reused birth not treated as unclean or watched.
  - **Blockers / agreed deferrals**: none

- [x] **Step 3: Tray**
  - **Implementation**: `tray.py`: a `helper.Peer("helper", "helper.json")` polled on the monitor's one-second tick (records the helper's exit code as `peer_exited`); `beat()` writes `updated_at` into `tray.json` on every tick and at setup (a failure is recorded once, message-free, and never ends the observer); `helper.ended_without_stop("tray", "tray.json")` runs before the first `tray.json` write; start line carries `version` and `python`; `exit_failed`, `observer_failed` and `tray_setup_failed` now carry type, message and traceback; the peer handle is closed in the final cleanup. The shared `failure()` is imported as `error_fields` because `failure` is already a local dict in `tray.py`. Also made `event_log.timestamp()` return `None` for an unusable time (Windows rejects very small timestamps), so an odd heartbeat cannot drop the unclean-end line. New `tests/test_keep_awake_tray_lifecycle.py` (4 tests).
  - **Verification / result**: `python -m unittest discover -s joro-awake/tests -p "test_keep_awake*.py"` → 62 tests, OK (31 + 13 event log + 14 helper + 4 tray). `tray.run` was exercised end to end with a fake `pystray` icon, a unique `KEY` and a temporary state folder: a real killed child standing in for the helper produced `peer_exited` with `0x00000001`, a dead leftover `tray.json` produced the unclean-end line with its PID and heartbeat, `tray.json` heartbeat advanced while running and was removed on exit.
  - **Blockers / agreed deferrals**: none

- [x] **Step 4: Docs and version**
  - **Implementation**: rewrote the Log section of `joro-awake/README.md` in place (what the log now records, the fault files, the 256 KiB cut-back, no automatic restart, paths in tracebacks); rewrote the event-log row in the parent `README.md`; rewrote the log sentence in `joro-awake/procedures/keep-awake.md`; `joro-awake/VERSION` is `0.1.1` (trailing newline kept). No new source file, so the installer `FILES` list and the package builder are unchanged.
  - **Verification / result**: `python -m unittest discover -s joro-awake/tests -p "test_keep_awake*.py" -v` → Ran 62 tests, OK. `python -m unittest discover -s tests -p "test_*.py" -v` → Ran 1 test, OK (package test, reads the new VERSION). Nothing was committed; changes are uncommitted in both repositories.
  - **Blockers / agreed deferrals**: none

- [x] **Step 5: Install and prove on this machine**
  - **Implementation**: Supervisor added two exit-code meanings (`0x40010004` logoff or shutdown, `0xC00000FD` stack overflow) to `event_log.py`, re-ran both suites (62 OK, 1 OK), then ran `joro-awake/setup-scripts/install_keep_awake.py`, `exit` and `start` at 16:38. Installed copies of the three source files and `VERSION` compare identical to the source tree; the Claude settings file hash was unchanged by the install.
  - **Verification / result**: Start lines carry `version 0.1.1` and `python 3.13.5`; `crash-helper.log` and `crash-tray.log` were created. `taskkill /F` on helper PID 96448 → tray logged `peer_exited` `0x00000001` at 16:39:05, and the next start logged `previous_run_ended_without_stop` with `last_heartbeat 16:39:04`. `taskkill /F` on tray PID 79744 → helper logged `peer_exited` `0x00000001` at 16:39:12, and the restarted tray logged its own `previous_run_ended_without_stop` with `last_heartbeat 16:39:11`. Final status: running, `power_requested` true, no diagnostic error. Not exercised at runtime: a traceback from a real helper-loop exception (unit-tested only), a native fault dump in the installed build (unit-tested with a real crashing child), and a stall line from a real sleep.
  - **Blockers / agreed deferrals**: The Run value `JoroKeepAwake` is present after the install. It was not read before the install, so "as before" is unproven; the installer reported `startup_enabled_by_install: false` and no step ran `startup-on`.

- [x] **Step 6: Commit and push**
  - **Implementation**: Run after the quality review and its fixes, so the pushed code is the reviewed code. `joro-awake` was detached at `f3519d1`, equal to its remote `main` after a fetch; checked out `main`, committed `a85721b` and pushed. The parent commit that contains this entry moves the submodule pointer to `a85721b` and carries the README row, this plan and the QA checklist.
  - **Verification / result**: `git ls-remote` for `joro-awake` returned `a85721b` on `refs/heads/main`. The parent's remote ref is read back after its push and reported in the session, since a commit cannot record its own hash.
  - **Blockers / agreed deferrals**: No GitHub release, by decision 1.

## Quality Review
*Filled by Step 7 (delegated to `/analyze-code-quality` in embedded mode). **Static** review — answers "is the code clean?".*

- **Scope**: `joro-awake/scripts/windows/joro_watcher/event_log.py`, `joro-awake/scripts/windows/keep_awake.py`, `joro-awake/scripts/windows/joro_watcher/tray.py`, the three new test files, `joro-awake/README.md`, `joro-awake/procedures/keep-awake.md`, `joro-awake/VERSION`, parent `README.md`. Matches `git status --short` in both repositories; no discrepancy.
- **Quality Standard**: not found — freeform review by the supervisor.
- **Findings**:
  1. Medium — `keep_awake.py` stall check measures the gap with `time.monotonic` only. Whether that clock advances while Windows sleeps was not verified here, and showing a sleep is what the line is for.
  2. Low — `keep_awake.py` `ended_without_stop` swallows every exception, so a failure to produce the unclean-end line leaves no trace.
  3. Low — `joro-awake/README.md` Log section: the new material is one fourteen-line paragraph.
- **Fixed**: all three, on Alvi's "proceed". (1) The stall check measures both the monotonic and the wall clock and records a stall when either gap passes ten seconds, with both values. (2) `ended_without_stop` ignores only a missing file and records any other failure as `unclean_check_failed` by type. (3) The README Log section is a table of entries. Two tests added; 64 Joro tests and the 1 package test pass. Reinstalled and restarted at 16:42; installed files match the source, status running with `power_requested` true.

## QA Handoff
*Filled by Step 8 after Quality Review is resolved. This plan is **not** runtime-verified — this section records the plan for that verification, which happens in a QA session with the stack up.*

- **Scope**: helper, tray and logger in `joro-awake/scripts/windows`; docs and version.
- **QA instrument**: Set up (`qa/qa-map.md` and the bench under `qa/`).
- **Integration coverage**: N/A — no step crosses a dependency a test would have to double; tests use real temporary folders and real child processes
- **Checklist**: `qa/checklists/crash-log.md`
- **Coverage split**: 1 automated check (64 named tests behind 9 coverage rows) / 12 manual — of which 1 is UI-bound
- **Runtime verification**: **NOT DONE** as a QA pass. The happy path was observed once during step 5. Next action: `/run-qa-test --checklist qa/checklists/crash-log.md`.
