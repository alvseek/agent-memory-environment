# Claude completion signals — QA checklist

**Source:** [Investigation plan](../../plans/2026-11-20-joro-claude-completion-signals.md). Verify the metadata probe and attribution of a disposable VS Code session's events. A `Stop` is a callback, not proof that foreground work ended. A missing claim after closure does not identify which cleanup path removed it.

## Happy path — manual, UI-bound

- [ ] In an approved disposable workspace, draft the settings into a fresh scratch folder. Confirm the events folder is empty. Activate only the owned workspace configuration, noting its hash and any inherited hooks. In the test tab request a no-tool reply; match its submit and Stop to the same session, prompt and Joro claim **before** closing it. Close only that tab. Look for its matching SessionEnd and check its claim again. Record the client version, check time and any missing evidence. Other sessions' claims may still exist. Remove only unchanged, owned capture settings.

## Isolation and failure checks

Run `python -m unittest discover -s qa/scripts -p test_claude_signal_capture.py -v` from the parent repository.

| Checklist item | Automated test | Still manual |
|---|---|---|
| Invalid command paths leave no new directories; linked ancestors are rejected. | `test_invalid_draft_command_creates_nothing`, `test_draft_rejects_linked_ancestor_before_creating_directories` | Junction detection uses a test double; verify a real junction below. |
| A partial write allows retry, preserves a foreign file, and an existing draft cannot be overwritten. | `test_failed_draft_write_rolls_back_without_removing_foreign_file`, `test_draft_is_inert_and_refuses_overwrite` | Workspace activation and cleanup are separate from drafting. |
| Concurrent callbacks publish separate, complete metadata records without copying prompt text or tool arguments. | `test_concurrent_processes_publish_complete_unique_files`, `test_only_allowlisted_metadata_survives` | Client delivery and attribution require the happy path above. |

- [ ] **Manual, filesystem:** In disposable storage, point a Windows directory junction at an empty scratch folder. Request a draft beneath the junction. Expect refusal and an unchanged target. Remove only the owned junction and scratch directories.

## Result

*Not yet run. `/run-qa-test --checklist` writes this section — see its Run record.*
