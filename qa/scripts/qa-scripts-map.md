# QA Scripts Map — Joro

> Last scan: 2026-11-11. Scanned the root README, plans and docs/scripts/tests/procedures trees.

**Category status**: exists-documented
**Owner**: /build-qa-bench

## Found

| Material | Location | Grade | Notes |
|---|---|---|---|
| RESET/INJECT/ACT/OBSERVE entry points | [bench.py](bench.py) | exists-documented | All four indexed roles independently found as functions and CLI phases; real finite-child smoke passed. |
| Rig guard/regression checks | [test_bench.py](test_bench.py) | exists-documented | README links the invocation; passing tests include broken evidence, process identity and target-safety controls. |
| Disposable Claude experiment | [claude_lifecycle_probe.py](claude_lifecycle_probe.py) | exists-documented | Real allow/deny paths were measured after quota reset. The classic-hook resume gap blocks the proposed wait-release design; this is SDK-path evidence, not interactive-terminal parity or watcher verification. |
| Real Windows request-handle integration checks | [test_power_requests.py](test_power_requests.py) | exists-documented | Linked from README; actual two-second system/execution requests and cleanup passed, including an actual close-omission red/restore/green run. No stage fixture required. |
| Request state/error-path unit checks | [test_power_state.py](test_power_state.py) | exists-documented | Linked from README; API doubled, so these do not claim native or battery evidence. |
| Coordinated DC/locked host observer | [battery_endurance_probe.py](battery_endurance_probe.py) | exists-documented | Read-only native preflight passed; actual endurance result pending. No forced lock/sleep or policy changes. |
| Endurance-evidence classifier checks | [test_endurance_evidence.py](test_endurance_evidence.py) | exists-documented | Synthetic data only; cannot count as battery protection proof. |

## Gaps

- ACT currently allows only its own fixed specimen. Sustained native host-power, actual client lifecycle and full watcher checks remain pending; neither the rig smoke nor a closed native handle establishes those outcomes.
