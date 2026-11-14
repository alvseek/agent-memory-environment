# Quick Wizard Plan: Joro Awake source preview

## Inherited Context

**From the parent plan**
- None — not a sub-plan.

**From pre-planning discussion**
- 2026-11-14: "specifically for joro awaken, I want you to create a separate repo
  for this, add licenses, and create a release."
- Purpose: "just a form of testing if I can market a product".
- License: user chose MIT after comparing it with Apache.
- Source/Python preview now: "A for now, but we should B before I can market it".
  A no-Python executable is required before marketing, not part of this change.
- "the original agent-memory-environment has to have the joro-awake, it will
  provide the python script to be downloaded like the einherjar wheel".
- User chose package preparation now, serving endpoint later.
- User approved the revised six-step QW plan: extract, submodule integration,
  package, document, verify, publish.
- Planning stays with parent; implementation delegated through Einherjar to
  opencode-go/deepseek-v4.1-flash (DeepSeek V4.1 Flash 1017).
- Later steering: "please continue the QW for the submodule in the background.
  let me know if there's a blockage. but the default is to implement plan until
  finished".

## Objective

Publish a standalone MIT-licensed source preview, retain one runtime source of
truth via the parent submodule, and prepare downloadable Python artifacts without
changing the running helper or creating a server.

## Confirmed Decisions

| Decision | Chosen | Reason |
|---|---|---|
| Parent integration | Root joro-awake submodule and forwarding installer | Product owns code; environment owns inclusion/distribution |
| Packaging | Explicit file allowlist; versioned ZIP and SHA256SUMS in ignored dist/ | Exclude private state and Git data |
| Release gate | Worker prepares draft; parent reviews then publishes prerelease | Independent verification before release |
| Compatibility | Existing installed paths unchanged; root installer forwards | No live config/runtime migration in this task |

## Success Criteria

- [x] Standalone public repository, MIT and dependency notices.
- [x] Parent pins pushed child commit as submodule; duplicate runtime removed.
- [x] Complete source ZIP/checksum, no private paths or binary environment.
- [x] Tests pass from clean extraction; forwarding installer help works.
- [x] Independent static/content review completed.
- [x] Public prerelease and anonymous download verified.
- [x] Installed runtime/settings unchanged; limitations stated.

## Execution Steps

1. Extract source and portable tests (crosses: filesystem).
2. Add legal/public docs and release version (crosses: filesystem).
3. Integrate parent submodule, wrapper and artifact builder (crosses: Git/filesystem).
4. Test archive and review changes without installing.
5. Push child before parent gitlink; prepare draft assets (crosses: GitHub).
6. Parent independently review, publish, and verify anonymous downloads.

## Execution Record

- Worker: Einherjar session ses_f9fa5c2839f84e34b9e90d6bef6b763c. Actual final
  session message names provider opencode-go/model deepseek-v4.1-flash.
- Einherjar's cp1252 reader threads failed decoding stdout/stderr; its reply
  envelope misleadingly said completed with zero bytes. Recovered the last text
  message from OpenCode's own message API; did not rerun/duplicate implementation.
- Child public repo: https://github.com/alvseek/joro-awake. Main and annotated tag
  v0.1.0 resolve to f3519d1a45029c01862dfdd69a84a93ffc55f418.
- Parent product integration commit: 8f9bae7f5eb7d7736eb5140f1b1ce0927bd98fca,
  pushed to origin/main; HTTPS submodule URL and exact gitlink independently read.
- Child retained runtime-relative layout. Installer now includes VERSION and
  derives its manifest version from that file; portability test no longer
  requires a precreated OpenCode temp directory.
- Parent removes duplicate runtime/adapters/procedure/product tests, retains the
  forwarding setup-scripts/install_keep_awake.py, adds allowlisted package builder
  and package test, updates README/live QA imports, preserves historical records.
- Independent runs: 31 child tests passed; 1 parent package test passed; wrapper
  --help exited 0 without installing; diff whitespace check clean.
- Downloaded both draft assets for independent review. All 22 archive entries
  matched exact tagged Git blobs, every installer input present, no Git/cache/
  private environment files or known private workstation paths. Runtime files
  match the prior parent commit byte-for-byte. Third-party license files match
  original installed metadata byte-for-byte.
- Clean temporary extraction passed 31 tests; extracted installer --help passed.
  This is NOT a full clean-machine installation/uninstall test.
- Published GitHub prerelease v0.1.0 (release ID 445097366) only after review:
  https://github.com/alvseek/joro-awake/releases/tag/v0.1.0.
- ZIP SHA-256:
  62807d248b4f5adecd6c597540a984d4a5d154dc756af41308d3baed88fcddfa.
  Matched SHA256SUMS, downloaded bytes, and GitHub asset digest.
- Source ZIP bytes vary across rebuilds because ZIP entry timestamps are retained;
  contents are stable. Published checksum identifies the actual uploaded artifact.
- No installed helper restart/stop/update, client settings change, startup change,
  server, signing purchase, Store submission, or binary packaging performed.

## Quality Review

- Scope: child tracked source/docs/tests/licenses; parent integration commit
  8f9bae7 and this evidence/checklist addition. The concurrently authored Windows
  installer High Wizard draft is separate and is not staged by this work.
- Quality Standard: none found; error handling, state/UX, efficiency, security,
  cleanup and consistency reviewed.
- Findings: no blocking findings in extraction/packaging. Behavior retained;
  packaging metadata/allowlist and exact release identity checked independently.
- Fixed: child portability/version changes were part of implementation.

## QA Handoff

- Scope: source extraction, wrapper, submodule and downloadable package.
- QA instrument: parent has exploratory map/bench; child has focused tests but
  no dedicated QA bench.
- Integration coverage: existing real-filesystem tests retained and passed;
  parent archive test crosses real filesystem. No new native desktop proof.
- Checklist: qa/checklists/joro-awake-source-preview.md.
- Runtime verification: archive/test/download checks performed; full native
  install/UI/sign-in/uninstall verification NOT DONE. No-Python marketing release
  and Store-first distribution are owned by the separate High Wizard plan.
