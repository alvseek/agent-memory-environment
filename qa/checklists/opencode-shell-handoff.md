# OpenCode background shell handoff — QA Checklist

**Source:** [Approved plan and execution evidence](../../plans/2026-11-25-agent-memory-environment-opencode-shell-handoff.md).

**Purpose:** Catch both a premature release that interrupts work and a stale request that keeps the PC awake after work ends.

**Apps under test:** The candidate Joro adapter and helper with OpenCode Desktop service **2.4.1** on Windows. Use a private service/session and helper state directory. The installed Joro, Einherjar, account credentials and Windows power policy are not modified.

A *claim* records which shell or parent needs protection. A *native request* is what the helper actually asks Windows to honor. The screen going dark is not itself evidence that Windows slept.

## Happy path — run this first

1. Arrange an idle window on AC, lid open. Let other agents and long-running jobs finish. Use a regular Windows console or Explorer; starting the test as an OpenCode managed shell would add an independent keep-awake claim and mask the result.
2. On this workstation, use **Win+R** to run `"%LOCALAPPDATA%\Temp\opencode\joro-handoff-sol\Screen-off check.cmd"`. This is the disposable fixture prepared for this session; it copies the candidate from the dedicated product worktree into a fresh private service, using a loopback model. If those temporary files or the worktree are unavailable, reprepare the fixture rather than substituting the installed adapter.
3. Leave the laptop untouched. The test reads the actual plugged-in display and sleep timeouts and schedules the shell's return **90 seconds after the longer timeout**. It does not lock the screen, force sleep, or change a setting. Leave the laptop idle after the parent completes so Windows can sleep. Wake it normally when you return.
4. Record the run directory (`candidate-screenoff-*`), `screen-window.json`, the helper's native events, the parent execution and claims, and the Windows Kernel-Power events covering the interval. A passing script establishes continuity of the candidate's request, not the physical screen or sleep result by itself.

## Automated coverage

| Checklist item | Automated test | What still needs a physical run |
|---|---|---|
| The last shell claim must not disappear before the correct parent owns protection. An independent shell must still release. | `test_background_shell_claim_transfers_and_cleans_up` checks intermediate writes, parent identity, interruption, cancellation and human waits. Private 2.4.1 service runs in the plan check the actual event order. | Windows behavior while the display is off. |
| A temporary final-release failure must clear without another event; a delayed retry must not clear new work. | `test_failed_final_release_retries_without_events_and_cannot_clear_new_handoff` exercises repeated failures, queued and in-flight retries, and disposal. | Faults are injected into the publisher; no deliberate lock on live user files. |
| A publisher error must not stop observation of later shells. | `test_failed_release_does_not_end_event_observation_or_disposal_cleanup` checks subsequent events and final disposal. | This test alone cannot prove the native request was honored. |

## Manual checks

- [x] **Screen-off progress.** Windows recorded its screen-off phase before the returning shell finished; the parent completed in that phase. The candidate held the same native request throughout without a helper stall or discarded request.
- [x] **Release and sleep.** The last candidate claim cleared and its helper released the native request. Windows slept later. The installed helper held an independent request past the candidate's release, so its effect on sleep timing cannot be isolated.

## Result

**Run:** 2026-11-25, local time (UTC+07:00) · software-architect · Tactic C, operator-started `candidate-screenoff-14121-6122`.

**Automated:** 3/3 green in the focused adapter run. **Manual:** 2/2 walked using the operator run, helper traces and Windows events.

**Sign-off:** Not signed off. Candidate handoff and final release passed; the candidate's ability to keep this laptop awake on its own was not isolated.

Both AC timers were 60 seconds; Windows reported AC power and an open lid. The test adapter matched the reviewed candidate by hash and differed from the installed adapter. Candidate helper PID 12452 acquired its native request at 12:02:13.172. Windows entered its screen-off phase at 12:04:18.790. The shell returned at 12:04:45.118; parent `ses_deeeacc2fffeOCc20l1GnkKfmB` succeeded at 12:04:45.683. Claim history shows parent protection was published before shell protection ended. The helper closed the same request at 12:04:46.782. Both private processes exited.

| Finding | Owner | Status |
|---|---|---|
| Installed Joro also reported a request for OpenCode until 12:05:31.970. Windows then slept for 306.95 seconds and woke by power button at 12:10:39.021 (Kernel-Power 507). | QA | No product failure observed. The overlap limits attribution of host wakefulness to the candidate alone. |
