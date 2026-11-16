# Joro crash log — QA Checklist

**Source**: [approved plan](../../plans/2026-11-16-joro-awake-crash-log.md)
**Purpose**: Catch an ending that still leaves no record, a diagnostic that disturbs keep-awake, and a log that grows or leaks.
**Apps under test**: helper, tray, logger. The installer's file list, the client hooks and plugin, and
Windows power behavior are deliberately not changed. Nothing restarts a dead process; that is out of scope.

## Terminology & state model

- **State file**: `helper.json` / `tray.json` under `%LOCALAPPDATA%\Joro\keep-awake-state`. A clean stop deletes it; a leftover one whose process is dead means that run ended without a stop.
- **Peer**: the other Joro process. The helper watches the tray and the tray watches the helper through a process handle, and records `peer_exited` with the exit code.
- **Fault file**: `~/.joro/crash-helper.log` / `crash-tray.log`, written only by a crash below Python, plus one "started" line per start.

**Key invariants** (try to disprove):
- Every ending leaves at least one line: an exit code from the surviving process, or an unclean-end line at the next start.
- A diagnostic failure never releases the power request and never ends the helper or tray.
- One ending produces one line, not one per second.
- A hook or activity-report failure never records its message.
- The tray rewriting `tray.json` every second never breaks `start`, `exit` or the single-tray rule.
- The log and fault files stay bounded.

## Happy path — single end-to-end scenario

1. Install, `exit`, `start`. The two `start` lines carry `version` and `python`.
2. Kill the helper with `taskkill /F`. Within two seconds the tray logs `peer_exited` for the helper.
3. `start`. The helper logs `previous_run_ended_without_stop` with a heartbeat one or two seconds before the kill.
4. Kill the tray the same way. The helper logs `peer_exited` for the tray; `start` brings the icon back and the tray logs its own unclean end.
5. `status` reports running with the same `power_requested` as before step 2.

## Automated coverage

| Item | Automated test | Still manual |
|---|---|---|
| Exit code naming | `test_exit_codes_are_named_in_hex`, `test_peer_exit_code_of_a_real_child_is_recorded_in_hex`, `test_killed_peer_is_named_by_its_exit_code` | The codes Windows really gives at logoff, shutdown and a native crash of the installed build |
| Unclean end | `test_leftover_state_of_a_dead_process_is_an_unclean_end`, `test_no_leftover_state_or_a_live_process_is_not_an_unclean_end`, `test_unreadable_leftover_state_is_recorded_without_its_message` | Both processes dying at once; a reboot (PIDs reused by other programs) |
| Tray watches helper | `test_tray_records_the_helper_exit_code_heartbeats_and_leaves_no_state` (fake icon, real killed child) | The real tray across a helper restart: it must attach to the new helper |
| Stall | `test_gap_over_ten_seconds_between_ticks_is_a_stall`, `test_wall_clock_gap_alone_is_a_stall`, `test_normal_ticks_are_not_stalls` | A real sleep and resume; injected clocks say nothing about what Windows clocks do |
| Tracebacks and privacy | `test_command_error_records_type_message_and_traceback`, `test_publisher_failure_records_type_and_frames_never_the_message`, `test_event_failure_never_records_the_message` | A real hook failure in the installed build |
| Uncaught exceptions | `test_uncaught_exceptions_are_recorded_before_the_process_ends` | An exception inside a real pystray thread |
| Native fault dump | `test_native_fault_leaves_a_stack_dump` (real crashing child) | The installed helper under `pythonw.exe` |
| Bounds | `test_log_stays_within_five_files_of_one_mebibyte`, `test_fault_file_is_cut_back_once_it_passes_the_limit`, `test_oversized_entry_keeps_event_and_end_of_traceback` | Growth over days of real use |
| Diagnostics never fatal | `test_fault_log_failure_is_reported_without_raising`, `test_heartbeat_failure_is_recorded_once_and_never_raises`, `test_stop_after_an_error_says_so_and_still_releases_power` | A read-only or missing `~/.joro` on a live helper |

## Checks

- [ ] Automated: both suites pass with no change to `~/.joro` or the installed state.
- [ ] Manual: the happy path above, start to end.
- [ ] Manual: kill the helper twice in a row with a `start` between. The tray logs `peer_exited` both times, each with the right PID.
- [ ] Manual: kill helper and tray in one command. The next `start` logs an unclean-end line for each, and no `peer_exited`.
- [ ] Manual: leave Joro running for ten minutes with no state change. The log gains no lines.
- [ ] Manual: `stop`, then `exit` and `start` ten times in a row while the tray is running. No command fails on reading `tray.json`, and exactly one tray icon remains.
- [ ] Manual, UI-bound: after the tray is killed and `start` is run, one icon is back and its state matches `status`.
- [ ] Manual: sleep the PC for a minute and resume. One `stall` line appears whose larger gap is close to the time asleep.
- [ ] Manual: sign out and back in with Joro running. Note which lines the sign-out left, and whether the exit code is one the table names.
- [ ] Manual: make `~/.joro` read-only, start covered work, and confirm `power_requested` stays true and the tray shows a warning, then restore it.
- [ ] Manual: after an upgrade from 0.1.0 with Joro still running, the first 0.1.1 start does not fail on the older state files.
- [ ] Manual: read a day of real log and both fault files. No prompt text, tool content or credential appears; file paths are expected.
- [ ] Manual: uninstall leaves `keep-awake.log` and both fault files in place.

## Result

*Not yet run. `/run-qa-test --checklist` writes this section — see its Run record.*
