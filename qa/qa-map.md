# QA Instrument Map — Joro

> Audit refreshed 2026-11-14 across the whole project. The finite-probe rig remains exploratory, not the running watcher's verification system. Current product operation is in the [project README](../README.md); tray/log boundary coverage and visual checks are indexed below.

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
| Checklists | exists-documented | /generate-qa-checklist | [Checklists map](checklists/qa-checklists-map.md) |
| Fixtures | missing | /integration-test | [Fixtures map](fixtures/qa-fixtures-map.md) |
| Config | exists-documented | /build-qa-bench | [Config map](config/qa-config-map.md) |
| Scripts | exists-documented | /build-qa-bench | [Scripts map](scripts/qa-scripts-map.md) |
| Seeds | exists-documented | /build-qa-bench | [Seeds map](seeds/qa-seeds-map.md) |

## Verdict

The rig's four indexed phase links still resolve and agree with bench.py's functions and dispatch. Focused helper/tray tests and the tray/log filesystem integration tests are discoverable through the READMEs; no upstream fixture was required. The new [checklist](checklists/tray-and-logs.md) separates UI/native checks from automated coverage. Native desktop concurrency, sign-in/uninstall, and battery endurance are not established by the rig or filesystem suite. Historical native request evidence and minimal-scope closure remain in the [watcher plan](../plans/2026-11-11-joro-host-agent-setup/SP-1-agent-keep-awake.md).
