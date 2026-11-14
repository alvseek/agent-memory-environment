# Quick Wizard Plan: Joro tray and logs

## Inherited Context

**From the parent plan**
- None — not a sub-plan.

**From pre-planning discussion**
- Discussion: 2026-11-14.
- Agreed scope: "tray Icon: when not active (not detecting any opencode / claude agent) it shows zzz icon, when active it shows eye icon."
- Settled: show actual keep-awake request state, not merely an open client process; warning when unavailable or observation fails; status tooltip.
- Settled: "offer exit directly is good for now. no need for Hide tray icon".
- Settled: warning remains after helper failure, "removed only on real exit".
- Added scope: "let's add log so we know what happened. we can put the log in ~/.joro/".
- Rejected: Hide tray icon; additional monitoring controls.

## Objective

Show Joro's actual keep-awake state in the Windows tray and retain bounded,
privacy-conscious diagnostic history without changing activity or power policy.

## Confirmed Decisions

| Decision | Chosen | Reason |
|---|---|---|
| State | Zzz idle, eye active, warning unavailable/error | Distinguish idle from failed monitoring |
| Tray | Separate pystray/Pillow process in an isolated environment | Reuse Windows shell integration and survive helper failure |
| Exit | Stop helper, confirm exit, then remove tray | Never silently remove the last visible failure signal |
| Launch | Start with helper, prevent duplicates | Existing manual/sign-in paths remain usable |
| Log | Transitions and errors only; no prompts or tool contents | Useful history without polling noise or private content |
| Retention | Five files total, at most 1 MiB each | Bound disk use |
| Delivery | Install and restart on this PC | Approved by Alvi, preserve sign-in startup setting |
| QA | Focused and isolated integration checks | Existing exploratory bench cannot prove new tray behavior |

## Success Criteria

- [x] Correct icon/tooltip mapping including errors.
- [x] Duplicate prevention and coordinated Exit.
- [x] Safe bounded shared logging.
- [x] Existing hook behavior and startup setting preserved.
- [x] Unit tests passing for testable logic.
- [x] Static quality review resolved.
- [x] QA checklist recorded.
- [x] Installed and restarted; visual verification reported separately.

## Execution Steps

1. Add tray model, rendering, monitoring and Exit (crosses: Windows/process/filesystem).
2. Add shared rotating event logging (crosses: filesystem).
3. Connect launch, isolated dependency install and uninstall; update docs (crosses: filesystem/process).
4. Run unit and approved boundary integration checks.
5. Static quality review and QA checklist.
6. Install/restart and verify installed processes/logs (crosses: Windows/process/filesystem).

## Execution Record

- Approved by Alvi before implementation.
- Baseline working tree clean.
- Relevant source and tests read; no quality-standard.md found.
- QA bench built; `python qa/scripts/bench.py observe` returned ok=true,
  child_exited=true, watcher_verified=false, battery_verified=false.
- Tray, bounded shared logger, launch/exit and installer source implemented.
- Focused unit suite: 20 tests passed, including the 13 existing helper/installer tests.
- No installed state or sign-in startup settings changed yet.
- Filesystem integration specification approved by Alvi.
- Added real filesystem checks for rotation and published-report interpretation;
  native lock/process checks and UI stay doubled in those tests.
- Both checks passed, failed under deliberate rotation/state mutations, and passed
  again after restoration. TemporaryDirectory owns cleanup; no upstream fixture.
- Full focused suite: 22 passed. `git diff --check` clean.
- After approved review fixes, final focused suite: 30 passed; diff whitespace clean.
- Checklist created; QA maps refreshed from a whole-project scan. All four rig
  links still resolve to the scanned phase functions/dispatch. Added documented
  test/checklist entries; no saved upstream fixtures or pending fidelity claims.
- Installed pystray 0.19.5, Pillow 12.3.0 and six 1.17.0 in the private environment.
  Manifest-owned installed files all hash-match the manifest.
- Before update, the existing helper was not running despite live OpenCode claims.
  No cause for its previous exit was established in this change.
- Started new helper/tray, repeated start twice: same helper PID 46024 and tray
  PID 6024. Observed actual log transition idle -> awake with OpenCode.
- Real CLI stop: helper exited; tray PID 6024 remained alive and logged warning.
  Real CLI exit: tray process exited and tray.json was removed. Restart succeeded.
- Final helper PID 27044; power_requested=true, clients=[opencode],
  uncertain_claims=0, diagnostic_error=null. This is native request issuance,
  not battery/locked-screen endurance proof.
- Installer preservation: Claude settings hash unchanged, OpenCode plugin hash
  unchanged, HKCU Run value unchanged (absent; startup remains OFF).
- Disposable native logging smoke: four real processes wrote 1,000 events across
  actual named-mutex/rotation code. Five bounded files remained, with 706 retained
  parseable records; older records rotated out as intended. Temporary logs and
  the owned temporary smoke script removed.
- Desktop-control tools unavailable: visible tray icons/tooltip/menu interaction
  were not inspected or clicked. No human QA sign-off was claimed.
- After delivery, Alvi confirmed the awake icon is visible: "yes, I can see a
  green monster eye watching lol". This confirms the green eye's actual appearance,
  not idle/warning appearance, tooltip, menu, or full checklist sign-off.
- At initial delivery, no commits or pushes had been performed; project wrap-up
  subsequently authorized committing and pushing this session's work.

## Quality Review

- Scope: README.md, procedures/keep-awake.md, scripts/windows/keep_awake.py,
  setup-scripts/install_keep_awake.py, scripts/windows/joro_watcher/event_log.py,
  scripts/windows/joro_watcher/tray.py, tests/test_keep_awake_tray.py,
  tests/test_keep_awake_filesystem.py, and this plan. Matches git status.
- Quality Standard: not found; focused freeform static review.
- Dimensions: error handling, state/UX completeness, efficiency, security, cleanup,
  consistency reviewed; project-specific standard not applicable.
- Findings:

| # | Severity | Location | Finding | Recommended correction |
|---|---|---|---|---|
| 1 | Critical | keep_awake.py run(); event_log.py record() | Tray startup or log failure can stop keep-awake; logging's default emit can also silently swallow failures | Decouple diagnostics from power loop; expose diagnostic failure in status/tray, retain errors without recursive logging |
| 2 | Critical | tray.py monitor()/setup() | Uncaught observer/setup failure can leave a stale healthy icon or unusable tray alive | Catch failures, show warning, retry observation; explicit readiness failure cleanup |
| 3 | Medium | tests/test_keep_awake_tray.py | New duplicate/Exit/startup paths lack focused failure-path tests | Add deterministic lifecycle tests using substituted UI/process APIs |

- Fixed: Alvi approved A (all three). Diagnostics no longer gate power acquisition;
  log failures surface without raising; observer failures warn/retry; setup failures
  close rather than leave an unmonitored icon. Added failure/recovery, duplicate
  launch and confirmed-Exit tests. Focused suite now 30 passing tests.
  Re-reviewed the corrections and added QA/docs scope; no remaining static findings.

## QA Handoff

- Scope: tray, helper lifecycle, logging, installer.
- QA instrument: existing exploratory map + bench.
- Integration coverage: approved filesystem tests ran; red/restored-green proof,
  temporary teardown verified by successful reruns. Native concurrent logging and
  installed CLI lifecycle additionally smoke-tested, not substituted for UI proof.
- Checklist: qa/checklists/tray-and-logs.md.
- Coverage split: 2 automated checklist items / 8 manual items, of which 5 are UI-bound.
- Runtime verification: installed CLI/process/log smoke performed; Alvi confirmed
  the green eye is visible. Full checklist NOT DONE; remaining visual states,
  tooltip and native menu are NOT RUNTIME-VERIFIED. Next:
  `/run-qa-test --checklist qa/checklists/tray-and-logs.md`; inspect the tray
  (including Windows overflow), idle/awake changes and actual Exit menu.
