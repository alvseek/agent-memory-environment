# Joro keep-awake — minimal local implementation

## Scope and decisions

This is SP-1 of the [Council plan](core-plan.md), covering the first-priority watcher only. Read/output limits, sounds, model configuration and anchor migration remain later work.

Alvi stopped the earlier design as too complicated and accepted the recommendation to cut back to a minimal implementation with focused tests: "go". That decision supersedes the earlier SQLite/registry architecture, elaborate release scaffolding and pre-build orchestration. The exploratory QA files are retained, not deleted or expanded as the product architecture.

Settled behavior:

- Windows first; Claude means Claude Code, not ordinary Desktop/browser chats.
- No MCP server, network listener, GUI or power-plan timeout edits.
- Local installation, manual start/stop/status and optional Windows sign-in startup. Installation does not start the helper or enable startup silently.
- Claude retains protection during permission prompts, explicitly chosen with "ok A" after the real approval/resume gap was measured.
- A Claude Stop hook can continue work, so it is not treated as a terminal event. Use the client's matching idle notification or session/process end; if idle identity is missing, retain protection conservatively until end/manual stop. This may delay idle release by about a minute.
- OpenCode uses context/compaction hooks and session.wait for new executions, plus independently tracked managed shells. Permission/form waits suspend only foreground work. Existing in-flight jobs and detached descendants are not retroactively discovered in this first version.
- Battery/locked-screen protection remains a required **unverified outcome**, not a claim made by this installed prototype. Do not silently replace native requests with policy edits or a display hold.

## Implementation

| Piece | Location | Responsibility |
|---|---|---|
| Helper | [keep_awake.py](../../scripts/windows/keep_awake.py) | One per-user process; atomic activity files; PID plus creation-time liveness; OR across independent work. No database. |
| Native requests | [power.py](../../scripts/windows/joro_watcher/power.py) | Acquire, clear and close owned Windows system/execution requests; no policy changes. |
| OpenCode adapter | [index.js](../../integrations/opencode/index.js) | Emit activity, handle waits, release only its own producer and serialize state updates. |
| Installer | [install_keep_awake.py](../../setup-scripts/install_keep_awake.py) | Local copies, merged Claude hooks, discovered global OpenCode plugin, local skills and owned-file uninstall. |
| Agent procedure | [keep-awake.md](../../procedures/keep-awake.md) | Manual controls, explicit startup opt-in and uninstall preconditions. |
| Focused tests | [tests/](../../tests/) | Ownership/concurrency, delayed idle safety, process cleanup and settings preservation/idempotence. |

Runtime/install data is local under Windows Local AppData/Joro, outside Git. Existing user callbacks and settings are preserved. Uninstall requires active clients closed and a separate PowerShell window; it must not delete modified files or overwrite newer user work.

## Verification earned

- **13 focused tests passed**: independent work/producers, PID cleanup, stale/missing prompt identity, ignored nonterminal Stop, SessionEnd, repeated release and preservation/idempotence of settings merge.
- **Live helper smoke passed**: two synthetic live work entries requested native power; ending one retained protection for the other; ending the last released requests; start/stop returned to a stopped, empty state. This was not a battery endurance test.
- **Four native Windows integration cases passed**, with a real close-omission mutation producing the expected failing assertion, restoration and a passing rerun. Native error-path/unit checks are retained in the earlier QA area.
- **Installed twice locally** without duplicate hooks. OpenCode JSONC was verified byte-for-byte unchanged by the installation. The local skill was loaded through the actual harness.
- **Actual installed Claude hook exercised** in a disposable SDK/print session: its real ancestor process had an active Claude claim while the controlled tool ran, a Stop-hook continuation ran without a Stop-based release handler, prompt identity was present and no claims remained for that Claude process afterward. Ordinary terminal idle-notification timing is not proven by this SDK-path test.
- **Actual OpenCode V2 execution observed** in a private test server: context dispatch, controlled two-second tool start/finish and session.wait completion. An earlier probe did not execute its tool and was not counted as passing; exposing the test tool outside Code Mode fixed that instrumentation. The production global plugin was also observed active through the live API, at the API-returned home location; do not call that an explicit workspace-targeted check.
- Earlier independent rig checks passed **31 tests** before the minimal implementation; those include synthetic evidence tests and must not be added to the focused count as if they were all watcher integration tests.
- Both temporary OpenCode QA sessions were subsequently removed through the client API, after checking their exact IDs and `Joro QA <run-tag>` titles. The private probe output remains as local evidence outside Git.
- The installed helper is running (PID 60152 as last observed), with live OpenCode activity and `power_requested: true`; no uncertain claims were reported. Windows sign-in startup was independently checked and is **off**. This proves current request issuance, not sustained battery protection.
- Final focused rerun: all 13 tests passed, Python compilation and Node syntax checks passed, and `git diff --check` passed. Stripping only the manifest-owned Joro callbacks from current Claude settings reproduced the original backup's complete settings object, verifying preservation of all unrelated settings/callbacks. The local update left the same helper running. Project work was committed and pushed as `6074e8b` during wrap-up; the final wrap-up push captures this status correction.

## Remaining limits and completion status

The minimal helper is locally installable; this is **partial delivery of R1**, not completion of every original acceptance criterion.

- Battery endurance is unproven. The coordinated trial `endurance-e7dad5040701` timed out while arming, with **zero measurement samples**, unchanged policy and a closed native handle. It did not show either success or failure of sleep prevention. No automatic repeat is authorized merely by a general continuation.
- Full ordinary-Claude-terminal idle timing, all OpenCode permission/background/reload paths and Einherjar-launched behavior are not fully runtime-verified. The implementation reports native requests, not universal coverage.
- Sign-in startup is supported but was not enabled during installation. Registry round-trip and full uninstall are not claimed tested here; active work intentionally prevents uninstall.
- Source was pushed as `6074e8b` during wrap-up; no GitHub release/package artifact was published. No unrelated Council feature has started.

Before calling R1 complete, verify the remaining required live behaviors or explicitly agree a narrower finished scope with Alvi. Do not revive the larger framework merely to continue this small delivery.

## Historical investigation record

The following earlier execution notes are retained verbatim as history. Their old architecture, stage gates and step statuses are not the implementation instructions for this simplified version.
## **EXECUTION LOG**

Use this file as the implementation source of truth. Before each step, read its full action and acceptance conditions; after it, record changed files, commands, test counts/results, and evidence against those conditions. Only the bench, disposable client experiment and native-request primitive/tests exist; the full watcher and adapters are not implemented. A planned check is not a completed one.

### QA bench preparation — completed before feasibility probes

- Alvi confirmed the R/I/A/O build spec with "proceed". Created the guarded Windows finite-probe rig, synthetic seed, required-config inventory, runbook and executable README index; refreshed all category maps against actual files.
- Files: `.gitignore`, `qa/scripts/bench.py`, `qa/scripts/test_bench.py`, `qa/seeds/baseline.json`, `qa/config/REQUIRED.md`, `qa/runbooks/watcher-bench.md`, `qa/README.md`, QA map/sub-maps and the root README status.
- Executed `python -m unittest discover -s qa/scripts -p test_bench.py -v`: **16 tests passed**. The suite exercised actual child-process supervision/termination and creation-time identity; its negative controls refused missing/stale/false/malformed results, wrong owner/schema, an invented battery-success claim, wrong target/marker, unknown files and hardlinks. A CLI OBSERVE on broken evidence exited nonzero.
- Executed RESET → INJECT → ACT → OBSERVE after the final seed move. Run ID `0d935acbf6be4757aa2ceeaa95846bac`; child exit 0; OBSERVE reported `ok: true`, `child_exited: true`, `boundary: bench-child-process-and-files`, `watcher_verified: false`, `battery_verified: false`. An earlier smoke also passed; the latest result is the one retained in the default external sandbox.
- No watcher, client adapter, power request, battery/lock action, global client edit or startup registration ran as part of this smoke. All actual watcher feasibility steps below remain NOT STARTED. QA bench readiness does not establish an application stack is up.
- Map rescan: each of the four loop roles is independently found in the executable and resolved from the README. Runbook/config/scripts/seeds are documented. Fixtures/checklists remain missing; playbook is intentionally absent for the current single finite-probe rig.

| Step | Status | Implementation evidence | Test evidence |
|---|---|---|---|
| 1.1 | PARTIAL — decision needed | Added and corrected qa/scripts/claude_lifecycle_probe.py: disposable print/SDK path, one exact harmless Bash command, explicit temporary ask rule, stdio permission host and actual tool-entry markers. No global configuration edited. | After quota reset, controlled allow and deny paths ran. Allow executed one exact command and recorded real start/finish markers; deny executed none. Classic hooks exposed prompt-open and tool-finished, but no approval/resume hook between them. Proposed wait-release mapping therefore leaves resumed work unprotected; ask before amending it or changing adapters. Interactive-terminal parity and remaining lifecycle cases are still untested. |
| 1.2 | PARTIAL | Added scripts/windows/joro_watcher/power.py and __init__.py, qa/scripts/test_power_requests.py and test_power_state.py. Uses native reason-bearing request handles; no policy changes or display hold was executed. | Four native integration cases passed; close-omission mutation made the real two-second lifecycle case fail and unconditional cleanup closed the handle. Restored production close, verified the restore, then all 27 tests passed (16 rig, 4 native, 7 doubled state/cleanup). Sustained AC, battery and lock conditions remain untested. |
| 2.1 | NOT STARTED | — | — |
| 2.2 | NOT STARTED | — | — |
| 3.1 | NOT STARTED | — | — |
| 3.2 | NOT STARTED | — | — |
| 4.1 | NOT STARTED | — | — |
| 4.2 | NOT STARTED | — | — |
| 4.3 | NOT STARTED | — | — |

Definition of done: correct behavior, relevant passing tests, actual execution evidence logged, configuration/privacy invariants preserved, and no silently deferred acceptance criterion. Phase 1 failures are blockers, not an excuse to proceed with weaker semantics.

### Feasibility progress and next native boundary

- Three disposable Claude attempts produced no hook events and zero permitted commands. The first two retained insufficient error classification; a bounded redacted diagnostic on the third established the exact blocker: "You've hit your session limit · resets 2:10pm (Asia/Jakarta)". No retry is planned before that quota reset. Fixed the probe's classifier to recognize this wording. No transcript/model-output stream was ingested into this session.
- Alvi confirmed the native `/integration-test` DEFINE spec with "proceed". Boundary: PowerRequest against the real Windows power-request API; client activity, session registry and installer absent/doubled. No stage fixture was needed: allocation created the test's own disposable native handle, so no upstream fixture fidelity check applies.
- Actual assertion: create a handle, acquire system/execution requests for two seconds, release acquired counts, close the handle and verify invalidity with GetHandleInformation. Also exercised independent handles and error-path cleanup. The deliberate close-omission mutation made the real lifecycle test FAIL with "Native handle remained valid after close"; test-finally cleanup closed that handle. Restored `self.api.close(self.handle)`, verified no mutation marker remained, and reran the full suite: **27 tests passed**. Tests also verified exact set/clear call counts, partial-acquisition cleanup, cleanup failures, explicit-only display selection and preservation of a KeyboardInterrupt alongside cleanup errors. No test forced a sleep, changed power policy or exercised battery endurance.
- Read-only current-host measurements after the run: sleep timeout 600 seconds on AC and DC; display timeout 300 seconds AC and 180 seconds DC; hibernate timeout 0 AC and 2147483647 seconds DC. Power source Online; battery 62%. These are current measurements, not this session's changes and not the prior episode's numbers. A sustained DC test must cross the current 600-second timeout plus the documented 300-second extension, without shortening either.
- Next host verification is a separately coordinated battery/locked-screen test; plan approximately 16 minutes to cross that 15-minute boundary. Do not unplug, lock, hold the display, or start that test until Alvi is ready. The watcher is not complete, and no lower-priority Council work starts yet.
- Alvi agreed to coordinate the endurance test with "go". Added qa/scripts/battery_endurance_probe.py and test_endurance_evidence.py. It never locks/sleeps the machine or changes power policy; it waits for physical-console lock plus DC, holds system/execution requests only, and samples for 960 seconds. It reports condition changes, timer evidence excluding sleep, progress gaps, unchanged policy and handle cleanup. Other possible inhibitors are not excluded, so even a passing observation is not causal proof or full watcher verification.
- First coordinated launch completed without starting the observation: `endurance-e7dad5040701`, stop_reason `arm-timeout`, sample_count 0. DC plus lock was not observed together during its ten-minute arming window. This is neither a passing endurance result nor evidence that sleep prevention failed. The report confirms unchanged policy, no cleanup error and native handle closed. Alvi subsequently asked to continue.
- Continuation at 15:12 Asia/Jakarta: read-only preflight showed AC online, battery 79%, physical console unlocked and unchanged 600/600-second sleep timeouts. Do not blindly rearm another user-dependent battery wait. The Claude quota-reset time had passed, so independent lifecycle investigation resumed.
- The first post-reset Claude attempt completed with zero approved commands and zero hook markers; correctly reported as a failed probe, not successful lifecycle coverage. Corrected the instrument to use the actually offered Bash tool, an explicit temporary ask rule, `--permission-prompt-tool stdio`, and quoted slash-form paths for this install's Git Bash hooks. A subsequent allow probe reached its command. Added markers from the actual controlled tool body and paired it with a deny probe to rule out trusting model text as execution evidence.
- Definitive allowed-path report: `lifecycle-887ab57e6b2e/report.json`. One exact controlled command executed. Hook/marker order was SessionStart → UserPromptSubmit → PreToolUse → PermissionRequest → controlled_tool_started → controlled_tool_finished → PostToolUse → Stop → SessionEnd. The SDK host separately timestamped permission acceptance; no classic resume hook arrived before the tool body ran.
- Denied-path report: `lifecycle-955175391821/report.json`. Zero approved commands and no tool-body markers; SessionStart → UserPromptSubmit → PreToolUse → PermissionRequest → Stop → SessionEnd. This was a real permission denial, not a mock successful tool return.
- New technical decision required: keeping the exact classic-hook design plus release-on-permission-wait is unsafe for resumed long-running work on the observed SDK path. Option A is a conservative Claude turn-level hold that also spans permission prompts, explicitly amending the prior wait-release requirement for Claude. Option B retains the exact requirement and investigates a supported richer adapter/launcher; no such replacement is claimed proven. OpenCode's wait policy remains unchanged. Do not silently choose either or generalize SDK-path results into interactive-terminal proof.
- Alvi selected A with "ok A". Carry protection across Claude permission prompts, and continue checking terminal/idle and background behavior; this resolves the permission-resume design choice, not all Claude lifecycle acceptance criteria or the pending battery gate.
- Read-only preflight succeeded on this host after correcting the console API name and resolving the precise unbiased timer from the DLL that actually exports it. The final preflight reported AC online, battery 70%, physical console locked, sleep timeouts still 600/600 seconds. No native requests are held by preflight. All **31 tests passed** before launch (16 rig, 4 native integration, 7 doubled power state, 4 synthetic endurance-evidence checks). Launch of the coordinated background observation is authorized; result remains pending until its job completes.

---
