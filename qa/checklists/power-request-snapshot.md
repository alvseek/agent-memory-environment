# Check power requests… — QA checklist

**Source:** [Joro tray controls](../../joro-awake/README.md#controls). Use a test copy of this build on an interactive Windows desktop, with the tray running as an ordinary user. Use a session where exiting the test tray will not interrupt work.

## Happy path (manual, UI)

- [ ] While Joro shows the green eye for known test work, right-click the tray icon, choose **Check power requests…**, and approve the Windows administrator prompt. Expect one timestamped **Summary** window. The tray should still respond, and the helper should still show the same work as active.
- [ ] Compare **Summary** with **Full report** for that same snapshot. A `DISPLAY` request belongs under Display; `SYSTEM` belongs under System sleep; `EXECUTION` alone does not. If an owner and reason repeat under one Windows heading, the Summary count should match those rows in Full report; requests under another heading should have their own count. Where Windows shows the reason `Joro agent work is active`, look for the Joro label. A Python process name alone must not earn that label. If a category has no requester in this run, record it as unobserved rather than treating it as a tested case.

## Other paths (manual, UI)

- [ ] Close the window, run the check again, and decline elevation. Expect **Check didn’t complete** with a cancellation explanation, not an empty list or the previous snapshot. Close it and retry; Windows should offer a fresh check.
- [ ] With a snapshot open, click the menu item again. Expect no second prompt or viewer. Close the first window with Escape, then reopen the action; the new window should have a fresh timestamp.
- [ ] With a viewer open and test work finished, choose **Exit** from the test tray. The viewer should close along with the tray, without requiring a second click in the window.

## Automated coverage

| What the tests exercise | Test | What still needs a desktop |
|---|---|---|
| Request grouping, exact reason, unfamiliar entries and Unicode | `SnapshotTests.test_groups_and_only_marks_the_exact_reason`, `test_preserves_unfamiliar_sections_and_localized_text` | Compare against actual Windows report text on the test system. |
| Repeated requests keep the correct count, separate identities and untouched Full report | `SnapshotTests.test_repeated_requests_counted_per_kind_and_reason_but_full_report_keeps_every_entry`, `test_same_named_processes_from_different_paths_remain_distinguishable` | Check the counts against the other tab of the same snapshot. |
| Windows pipe transfer, unsuccessful command and cancellation cleanup | `WindowsTransportTests.test_real_pipe_preserves_output_and_rejects_failed_exit`, `test_cancelled_launch_cleans_up_pending_connection` | Actual UAC approval and denial from an unelevated tray. |
| Separate viewer process, complete report transfer and release of the single-check lock | `ViewerProcessTests.test_real_unelevated_child_receives_original_report_and_normal_or_failed_exit`, `TraySnapshotTests.test_viewer_failure_notifies_without_report_and_releases_guard` | Painted window, notification, close and retry. |
| Viewer shutdown signal and tray exit while a snapshot worker is busy | `ViewerProcessTests.test_stop_signals_real_child_through_stdin_and_worker_reaps_it`, `TrayLifecycleTests.test_tray_exit_does_not_wait_for_snapshot_worker` | An open native viewer closes on actual tray Exit. |
| Required viewer and query files reach the source package | `PackageTests.test_archive_has_every_installer_input_and_matching_checksum` | Launch from the intended test installation. |

## Result

*Not yet run. `/run-qa-test --checklist` writes this section — see its Run record.*
