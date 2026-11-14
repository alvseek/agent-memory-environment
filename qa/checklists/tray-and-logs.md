# Joro tray and logs — QA Checklist

**Source**: [approved plan](../../plans/2026-11-14-tray-and-logs.md)
**Purpose**: Catch misleading status, shutdown races and diagnostic regressions.
**Apps under test**: helper, tray, logger, installer. Client activity policy and
Windows power-plan/battery behavior are deliberately not changed or re-certified.

## Terminology & state model

Zzz = helper alive, no request; eye = helper reports a native request;
warning = helper unavailable/stale, uncertain activity, or diagnostic failure.
`stop` leaves the warning. Exit stops both; it is not Hide.

**Key invariants** (try to disprove):
- An open idle client must not cause an eye.
- A dead helper or failed observer must not leave a healthy-looking eye.
- Diagnostic failure must not release a valid power request.
- Failed shutdown must not remove the tray.
- Multiple writers must not bypass retention or corrupt records.

## Happy path — single end-to-end scenario

1. Install, note existing startup setting, then start Joro twice.
2. See exactly one tray icon; hover and compare with helper status.
3. Let covered work become idle, then run covered work: see Zzz then eye.
4. Stop the helper: warning remains. Start it: state recovers.
5. Choose Exit: helper and tray exit. Start Joro again.
6. Inspect `~/.joro/keep-awake.log`; no prompts/tool content, no every-second noise.

## Automated coverage

| Item | Automated test | Still manual |
|---|---|---|
| State and clients | `TrayTests` presentation checks | Actual painted icon, tooltip and shell overflow |
| Failure/recovery | observer/log/startup failure tests | Real shell/permission failures |
| Exit | exit success/failure and confirmation tests | Native menu callback and actual process cleanup |
| Duplicate start | live-tray spawn test | Native mutex/readiness races |
| Retention | `FilesystemTests.test_log_rotation_keeps_five_bounded_files` | Real concurrent writers/native lock |
| Report reads | `FilesystemTests.test_published_helper_reports_drive_tray_states` | Live helper and timing |
| Hooks preserved | `InstallerTests` settings merge checks | Installed settings and startup registry |

## Checks

- [ ] Automated: focused suite passes with no installed state changes.
- [ ] Automated: rotation and report checks fail under deliberate defects and pass restored.
- [ ] Manual, UI-bound: one icon remains after repeated starts; eye, Zzz and warning are distinguishable at tray size.
- [ ] Manual, UI-bound: tooltip agrees with real status; opening an idle client is not enough to show eye.
- [ ] Manual, UI-bound: stopping the helper leaves warning; restarting recovers.
- [ ] Manual, UI-bound: Exit removes the tray only after helper shutdown.
- [ ] Manual, UI-bound: an actual helper crash cannot leave a healthy-looking eye.
- [ ] Manual: installed copies match source; unrelated hooks and sign-in setting are unchanged.
- [ ] Manual: overlapping real log writers leave parseable bounded history; no sensitive content.
- [ ] Manual: startup at a future sign-in, Explorer restart and uninstall are explicitly checked or left unverified.

## Result

*Not yet run. `/run-qa-test --checklist` writes this section — see its Run record.*
