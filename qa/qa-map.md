# QA Instrument Map — Joro

> Historical exploratory-bench audit, last scan 2026-11-11. The watcher was subsequently simplified; this map is not its current implementation inventory. See the [project README](../README.md) and [watcher plan](../plans/2026-11-11-joro-host-agent-setup/SP-1-agent-keep-awake.md). The finite-probe rig remains executable, but is not required to operate Joro.

## R/I/A/O loop maturity

| Phase | Grade | Backed by |
|---|---|---|
| RESET | exists-documented | [bench.py](scripts/bench.py), reset function and CLI phase |
| INJECT | exists-documented | [bench.py](scripts/bench.py), inject function; [synthetic source](seeds/baseline.json) |
| ACT | exists-documented | [bench.py](scripts/bench.py), act function and supervised finite child |
| OBSERVE | exists-documented | [bench.py](scripts/bench.py), observe function; healthy and broken-control tests |

## Index integrity — qa/README.md R/I/A/O table

All four README links resolve to bench.py. Its reset/inject/act/observe functions and CLI dispatch independently match the indexed roles. No dead or diverged link was found. Self-smoke proves the rig boundary only, not watcher/client/battery behavior.

| Phase | Index link | Resolves | Agrees with scan | Status in index |
|---|---|---|---|---|
| RESET | [bench.py](scripts/bench.py), reset | yes | yes | documented |
| INJECT | [bench.py](scripts/bench.py), inject | yes | yes | documented |
| ACT | [bench.py](scripts/bench.py), act | yes | yes | documented |
| OBSERVE | [bench.py](scripts/bench.py), observe | yes | yes | documented |

## Category maps

| Category | Status | Owner | Map |
|---|---|---|---|
| Runbooks | exists-documented | /build-qa-bench | [Runbooks map](runbooks/qa-runbooks-map.md) |
| Playbook | missing | /build-qa-bench | [Playbook map](qa-playbook-map.md) |
| Checklists | missing | /generate-qa-checklist | [Checklists map](checklists/qa-checklists-map.md) |
| Fixtures | missing | /integration-test | [Fixtures map](fixtures/qa-fixtures-map.md) |
| Config | exists-documented | /build-qa-bench | [Config map](config/qa-config-map.md) |
| Scripts | exists-documented | /build-qa-bench | [Scripts map](scripts/qa-scripts-map.md) |
| Seeds | exists-documented | /build-qa-bench | [Seeds map](seeds/qa-seeds-map.md) |

## Verdict

The isolated rig runs and its index resolves. Separate real Windows request-handle lifecycle tests have passed, including a close-omission negative control; this does not establish sustained battery protection. Actual client lifecycle and the full watcher remain unverified. No upstream stage fixture was needed for the native-handle test; feature fixtures/checklists remain pending their owning builders. No playbook is needed for the current single rig; add cross-component guidance when real helper/adapters exist. See the [watcher plan](../plans/2026-11-11-joro-host-agent-setup/SP-1-agent-keep-awake.md) for execution evidence and unproven acceptance criteria.
