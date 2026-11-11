# Joro QA — required configuration

| Input | Used by | Status | Source |
|---|---|---|---|
| Windows | Native process identity, mutex and path safeguards | Required; bench refuses other operating systems | Target host |
| Python 3.12+ | All four bench phases and their finite child | Python 3.14.0 verified on this workstation | Run `python --version`; use a resolved, working interpreter |
| Synthetic baseline | INJECT and finite child | Committed; no secrets | [baseline.json](../seeds/baseline.json) |
| Sandbox identity | All four phases | Derived from repository path plus `default` or a generated test name | [bench.py](../scripts/bench.py) |
| Windows Local AppData | Sandbox parent | Resolved through the Windows API, not a configurable data-store URL | `%LocalAppData%/Temp/opencode/joro-qa/` |

The default bench requires no API key, client login, real user settings, network service, watcher installation or power-policy change. There is no production-target switch. `--sandbox` accepts a name, never a path; commands refuse ownership-marker mismatches and linked targets. The separately invoked native integration suite briefly acquires real Windows system/execution requests and cleans them up; it does not force sleep or test battery endurance.

Claude Code/OpenCode credentials and coordinated physical power/lock conditions will be requirements of future real-client/host probes, not of this bench smoke. Those probes are not implemented or counted as passing here. Never commit private client config, tokens, transcripts or runtime evidence containing private data.
