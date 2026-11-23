# Quick Wizard Plan: When can Joro release an open Claude tab's keep-awake claim?

## Plan State

- **Source protocol:** `/hermod:quick-wizard --save`
- **Approval:** APPROVED for the read-only investigation, with the stated host-integration coverage limit.
- **Outcome:** Investigation complete. The interfaces reviewed do not justify a new automatic release rule for an existing VS Code tab. No runtime change or live test.
- **Confirmation:** On 2026-11-23, after reviewing the saved plan, Alvi asked to dispatch it through Einherjar using GPT-6.2 Sol with medium effort on the current branch (`main`). A live observation remains a separate decision: notify Alvi before BRYES is used and wait for his go-ahead because he is using the PC.

To resume, read the served procedure and this plan, check approval, and follow the first unfinished execution-log entry.

## Inherited Context

**From the parent plan:** None. The [completed signal audit](2026-11-20-joro-claude-completion-signals.md#execution-log) supplies the baseline; this is a follow-up, not a rerun.

**From pre-planning discussion (2026-11-23):**

- “Can Joro tell when Claude Code is genuinely waiting for the next prompt and has no work left in that VS Code session?”
- “Only run another live test if that source could distinguish cases the old signals couldn’t.”
- “Propose the smallest adapter change if the evidence supports it; otherwise, record exactly what Joro still cannot observe and stop there.”

The earlier audit found that an ordinary finish and a continued turn could produce identical `Stop` fields. A tab reported idle with a live background shell; cancellation could leave the claim held without a terminal callback. Timeouts, empty Stop lists and the absence of a callback therefore do not establish completion. Closing the tab was a different case.

## Objective

Determine whether a read-only signal available to Joro, alone or together with other current metadata for the same session, can distinguish a completed turn from continuing or outstanding work while the tab stays open.

## Specification

The test is about **one session's claim**. Other sessions and clients can still require the machine to stay awake. A candidate must establish both that the current foreground turn has finished after all Stop hooks (or that cancellation has settled) and that no relevant background work remains. Permission waiting is protected. A delayed event must not release a newer prompt's claim; missing, stale, invalid or inaccessible evidence must leave protection in place.

Use lifecycle metadata only: version, session/prompt/task identifiers, state and ordering as needed. Exclude conversation text, transcripts, commands and task output. Work in the parent repository for findings. This plan does not change the shipped adapter, install anything, clear claims, change power settings, or start cache warming.

## Confirmed Decisions

| Decision | Choice and reason |
|---|---|
| Evidence sources | Alvi selected A: inspect documented interfaces first. If insufficient, inspect read-only status metadata for the installed extension. Undocumented behavior is evidence for the measured build only. |
| Where a result would apply | The existing Claude hook feeds the session claim in [`keep_awake.py`](../joro-awake/scripts/windows/keep_awake.py). Identify how Joro could actually receive or read the candidate for that same session; an internal UI state that Joro cannot access is not an adapter input. No new integration is being built in this plan. |
| When to run a client test | Reuse the previous evidence to reject candidates on paper first. Seek separate approval for a bounded disposable observation only if it would answer a new question. |

## Success Criteria

- [x] Identify the exact source, field or event, who can read it, when it is updated and what work it covers. Distinguish documented guarantees, measured behavior and unknowns.
- [x] Compare candidates with true completion, continuation, cancellation, permission waits, new prompts and ongoing background work. No candidate met the live-test condition.
- [x] Record which facts are missing and which sources were checked. The negative finding completes the investigation; it does not establish a fix.
- [x] Review the changed artifact and record the QA handoff. No probe logic was added.

## Execution Steps

1. **Find a source Joro can read** (crosses: official documentation and local filesystem). Identify the target host/build. Check documented host interfaces for a post-hook foreground outcome, settled cancellation and current background state. If necessary, inspect installed extension declarations and status metadata without reading user content. For each serious candidate, record its provenance, identity, timing, coverage, and access path from Joro. Stop discovery if the available sources cannot provide a necessary fact.
2. **Try to disprove the candidate** (conditionally crosses: Claude Code in VS Code). Compare its predictions with the prior audit. Where the record lacks that signal, label the comparison unmeasured. If it could distinguish the cases, present the smallest discriminating observation for approval: target build/session, cases, permitted metadata, independent evidence of whether work continued, cost, setup and cleanup. After approval, test the candidate in that session. Skip the live run, with reason, if the same observations would fit both outcomes. Do not activate capture or start a paid turn on plan approval alone.
3. **Record the verdict in this file.** For each claim transition, identify the evidence supporting release or retention. State any known gaps and how an unsupported build would behave. Propose the smallest change only if supported; otherwise name what cannot be distinguished. Complete static review and QA handoff against the actual changes.

## Execution Log

Read the whole plan at start and after compaction. Verify each step and enter its evidence here before continuing. Respect the separate observation gate.

| Step | Implementation | Verification / result | Gate or deferral |
|---|---|---|---|
| 1. Find a source | Complete (offline): reviewed public interfaces first, then installed build declarations and process identity. | No usable open-tab release signal found; see dated evidence below. | No client launch or capture. |
| 2. Disprove or test | Complete (offline comparison): tested the proposed inferences against the prior audit, not a new client run. | Stop-only and bare-idle rules have measured counterexamples. New SDK/mod/telemetry events and the CLI JSON projection of this tab were not measured. | Skip live observation: no in-scope source exposes the missing evidence, and repeating the known status/Stop cases would not supply it. |
| 3. Record verdict | Coordinator reviewed the handoff and finalized the finding below. | Compared the documented mod event, external CLI fields and SDK session access with the prior VS Code observations and Joro's claim handler. | No desktop time or new capture needed. |

### Step 1 evidence — 2026-11-23

**Target and access.** The previous audit measured the VS Code extension and bundled worker on 2.1.301 and 2.1.327. Today the installed `C:/Users/alvia/.vscode/extensions/anthropic.claude-code-2.1.327-win32-x64/package.json` identifies Anthropic's extension as 2.1.327, and a live `claude.exe` path under its `resources/native-binary/` confirms that bundle is in use; this does not identify a particular tab or verify the binary via execution. The manifest declares a `claudeVSCodePanel` webview activation and editor, session-navigation, plugin and UI commands, but no public lifecycle/status command or proposed chat API; no `.d.ts` was shipped in that extension directory. The manifest is not proof that no private interface exists. Joro's [existing adapter](../joro-awake/scripts/windows/keep_awake.py#L182-L272) keys a claim by client, owner PID/birth, producer and session; it stores the hook `prompt_id`. A new source must bind to that same owner/session and current prompt or an equivalent generation, not just the project, tab title, or last event observed.

Official references below were fetched as public text on **2026-11-23**. These are current docs, not a contract pinned to either measured build.

| Surface | Documented signal, timing and limits | Access from Joro |
|---|---|---|
| [Hooks: Stop](https://code.claude.com/docs/en/hooks#stop), [Notification](https://code.claude.com/docs/en/hooks#notification) and [SessionEnd](https://code.claude.com/docs/en/hooks#sessionend) | Common `session_id`/`prompt_id` can identify work. `Stop` and `SubagentStop` task/cron lists are registry snapshots, present when reachable; `Stop` runs before the stop decision is settled, and another matching hook can continue the turn. User interruption can omit `Stop`; `StopFailure` is for API errors, not cancellation and drain. `PermissionRequest`/`permission_prompt` are evidence to retain. `idle_prompt` is delayed and the documented background-agent suppression is not a complete bound on shell/other work or VS Code delivery. `TaskCreated`/`TaskCompleted` are task-list events, not a live-work inventory; `agent_completed` is for background sessions with terminal agent view open. `SessionEnd` is closure/termination, not open-tab readiness. | Settings hooks are an existing delivery path. They expose positive reasons to retain, but no release-grade foreground-plus-background snapshot for the open tab. |
| [External status: `claude agents --json`](https://code.claude.com/docs/en/agent-view#list-sessions-as-json), [VS Code](https://code.claude.com/docs/en/vs-code), [VS Code Extension API](https://code.visualstudio.com/api/references/vscode-api#ChatResponseStream) | CLI status exposes live PID and `busy`/`waiting`/`idle`, `waitingFor` when waiting, and full `sessionId` when set; `state=done`/`failed`/`stopped` etc. is documented for supervised **background sessions**, not an ordinary IDE tab. Neither field set gives prompt generation, an accepted-stop/settled-cancel barrier or task/cron inventory. VS Code tab indicators, session-list filters, accessibility announcements and agent map are UI features; the built-in IDE MCP service is for IDE integration, not Claude turn observation. VS Code participant streams are for the participant's own responses, not for watching this extension's panel. | `agents --json` is a documented external polling surface; inclusion of the exact IDE panel and its fields on this build was not tested. Even if included, the documented fields are insufficient. No CLI was launched; no tab, logs, transcripts, job state files, or task output were read. |
| [Agent SDK Query/result](https://code.claude.com/docs/en/agent-sdk/typescript#sdkresultmessage), [session state](https://code.claude.com/docs/en/agent-sdk/typescript#sdksessionstatechangedmessage), [background set](https://code.claude.com/docs/en/agent-sdk/typescript#sdkbackgroundtaskschangedmessage), [session management](https://code.claude.com/docs/en/agent-sdk/sessions) | A host can consume final turn `result` outcomes, including optional terminal reason and client-supplied user-message UUID(s) on supported versions; that identity is not a documented alias for a hook's `prompt_id`. `interrupt()` is an action; its capability-gated receipt precedes the interrupted result and is only a queue snapshot. `queued_turn_count=0` omits synthetic and unmarked inputs. `canUseTool`/pending permissions cover the owning host's requests. Opt-in `session_state_changed` can be repeated, has session but no prompt ID, and `idle` may arrive before or after `result`; background shell commands do not hold `running` even with the [background-running default](https://code.claude.com/docs/en/env-vars#variables). `background_tasks_changed` carries a full live task set on membership changes (no initial event, reinitialize can supply a snapshot on supported versions); task notifications identify individual tasks/runs, not overall drain, and the live set alone does not attest scheduled wakeups or queued follow-up turns. | These are on the owning SDK host's stream (or a process it starts via print/stream JSON); Joro is not that host. `reinitialize()` presumes an existing transport, not a public way to join the VS Code panel. `listSessions`/`getSessionInfo` are history metadata with no live fields, and `resume` drives a session rather than passively observing the existing panel. Session messages and sign-in/Remote Control were not used. |
| [In-process Claude mods](https://code.claude.com/docs/en/plugins/mods/events#follow-a-turn), [reference](https://code.claude.com/docs/en/plugins/mods/reference), [public types](https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts) | Strongest foreground lead: `turn.start`/`turn.complete` share `turnId`; completion explicitly includes user interruption (`isAborted`); exclude subagent `agentId`. `session.stop` is raised before abort (2.1.326+), so it is not settlement. Public types expose a **current** `$.session.info().promptId`, not an immutable prompt ID on the completion event. No documented complete current task/cron inventory on `turn.complete`: `$.agent.list()` is subagents/teammates, not shell/monitor/workflow/MCP/cron coverage. `classic.Stop` exposes the same earlier snapshot. | A **new, loaded mod** could publish allowlisted metadata via a file/process bridge; it is not a passive reader of this tab as installed. Neither the exact-build ordering after Stop continuation and cancellation cleanup nor a race-safe join to current prompt plus background state is established. No mod loaded or built. The docs advertise VS Code support but public types are not version-pinned. |
| [OpenTelemetry hook completion and traces](https://code.claude.com/docs/en/monitoring-usage#hook-execution-complete-event), [status line](https://code.claude.com/docs/en/statusline) | Opt-in telemetry can report hook-batch counts with event/process ordering and correlate by `prompt.id`; `hook_execution_complete` means a hook invocation's batch finished, not that the host accepted the end of the turn or drained work. The beta interaction span has turn duration but no documented joint post-hook/cancel/drain guarantee or authoritative live registries. Status-line refreshes are display updates, not release barriers. | A configured exporter or status-line script would be additional instrumentation. No configuration, logging or capture was activated. |

### Step 2 comparison — 2026-11-23

Compared the documented fields with the [prior audit's measured cases and replay](2026-11-20-joro-claude-completion-signals.md#execution-log); did not reopen the underlying captures.

| Case | Prior evidence | Consequence |
|---|---|---|
| Ordinary finish vs. continued foreground turn | On 2.1.327, the ordinary turn and the first, blocked `Stop` of a continued turn both had `stop_hook_active=false` and explicitly empty task/cron lists. The continued turn later produced another `Stop` for the same prompt. On 2.1.301, the ordinary control had no captured `idle_prompt` in the observed window. | A fresh matching empty `Stop` still releases early; another quiet window cannot make absence meaningful. A host terminal event would need to identify the current turn only after the continuation resolves; SDK and mod candidate events were **not measured**. |
| Cancellation vs. settled cancellation | On 2.1.327, the tab reported idle while the cancelled tool child was still alive; a later sample found it gone before natural expiry. No terminal hook arrived within the observation window. On 2.1.301, owner remained live after the child had gone and no terminal callback was captured by the check. | Bare idle or a stop request is not cleanup completion. A host event would need positive evidence of settled interruption plus no outstanding work; SDK/mod events and the CLI JSON projection were **not measured**. |
| Permission wait and resume | Matching permission callbacks on 2.1.301 preceded a later `PostToolUse` and `Stop`; the 2.1.327 tab reported `waiting` for permission before work began. | Waiting is a retain signal. Answering the request removes that wait, not the remaining work. An SDK host's callback was **not measured** in the IDE. |
| Background work and wakeup | On 2.1.327, the tab reported idle with an independently live shell, and the inclusion of a running shell in `Stop` corroborated it. After exit the host became busy and a new prompt's `Stop` had empty lists. The 2.1.301 audit likewise recorded a new prompt and later empty lists after shell exit. | A positive running entry retains. Shell exit, task notification, launch `PostToolUse`, and a later empty snapshot are not proof that the wake turn or other work is finished. Other task kinds, SDK task sets, and the CLI JSON projection were **not measured** in these cases. |
| New/overlapping prompt; tab close | The wake turn had a different prompt ID. Prior stale-event replay was synthetic, not a measured competing-prompt race. A separately closed tab emitted `SessionEnd` and lost its claim; the audit could not isolate the callback from owner-death cleanup. | A valid future release needs a same-owner/session generation check at clear time so late events cannot clear new activity, including synthetic wakeups. A session-only status or an unlocked read-then-delete cannot establish this. Closure is a separate existing path. |

### Step 3 verdict

Keep the adapter unchanged. A mod running inside Claude can receive `turn.complete` for an ended or interrupted turn. Seeing that event would answer a foreground question, but would not tell Joro whether a shell or other work is still running. The richer SDK events belong to the session's host. We found no read-only interface that ties **both** facts to the current turn of the existing VS Code tab. Combining an earlier empty `Stop` list with a later completion event would still use an old snapshot.

Submit and tool activity continue to establish or refresh the claim. Permission waits and known work retain it. No new release on `Stop`, a cancel request, idle status, or missing, stale or unsupported metadata is justified. Matching `idle_prompt`, `SessionEnd` and dead-owner cleanup remain as implemented. In the earlier closure test the claim cleared; which cleanup path won was not isolated. Reopen the question if a supported source makes current background and queued work visible alongside settled foreground completion for the same turn.

## Quality Review

Reviewed this plan, the only workspace change reported by `git status --short`. Checked the distinction between documented events and observed behavior, who can read each signal, and the counterexample of a live shell in an idle tab. The report contains lifecycle metadata and does not rely on conversation text or task output. No unresolved static findings in the report; no runtime code or tests changed. No project `quality-standard.md` was found.

## QA Handoff

No feature or probe shipped, so no new runtime checklist applies. The [existing checklist](../qa/checklists/claude-completion-signals.md) covers the prior probe and remains unwalked. The [exploratory bench](../qa/README.md#the-riao-loop) tests its own finite process, not an open VS Code tab; its planning-time `observe` command found no default sandbox marker. There is no automated host-integration coverage. No new client behavior was runtime-verified, and no BRYES operation was performed.
