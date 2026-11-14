# QA Fixtures Map — Joro

> Last scan: 2026-11-14. Scanned the root README, plans and docs/scripts/tests/procedures trees.

**Category status**: missing
**Owner**: /integration-test

## Gaps

- Saved upstream stage fixtures: **NOT FOUND**. The [filesystem tests](../../joro-awake/tests/test_keep_awake_filesystem.py) cheaply create preconditions through real writers and own teardown, so no upstream fixture was needed. Existing helper tests publish activity through the real claim entry point. Bench seed inputs are not fidelity-proven client fixtures.
