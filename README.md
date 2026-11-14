# Joro — Agent Environment

Joro sets up the host an agent works on. Its first capability is a small local Windows keep-awake helper for Claude Code and OpenCode, with a status tray icon and bounded diagnostic log—no MCP server or power-plan edits.

## Install and use

Requires Windows, Python 3.12+ and the clients you want to integrate. From this checkout:

```powershell
python setup-scripts/install_keep_awake.py
python "$env:LOCALAPPDATA/Joro/keep-awake/scripts/windows/keep_awake.py" start
python "$env:LOCALAPPDATA/Joro/keep-awake/scripts/windows/keep_awake.py" status
python "$env:LOCALAPPDATA/Joro/keep-awake/scripts/windows/keep_awake.py" stop
```

Installation copies the helper locally, creates a private `.venv` with pystray and Pillow for the tray, adds Joro's Claude hooks and OpenCode plugin, and installs a `joro-keep-awake` skill for both clients. The first installation needs internet access to download the tray dependencies. It preserves unrelated Claude hooks and does not edit OpenCode's JSONC configuration. Installation does not start the helper or enable sign-in startup.

Start monitoring before beginning fresh work. Start a new Claude session after installing its hooks. OpenCode discovers the global local plugin automatically; existing in-flight jobs are not retroactively discovered by this first version.

Starting Joro also starts its tray indicator. Zzz means monitoring is idle and sleep is allowed; the eye means a native keep-awake request is active; a warning means monitoring stopped, failed, or cannot confidently read activity. Hover for the reason and active client names. An open client window alone does not mean awake. Windows may initially put the icon in the tray overflow.

`stop` stops monitoring but leaves a warning icon. Use the tray's **Exit**, or the `exit` command, to stop monitoring and remove the icon together. If helper shutdown fails, the tray stays visible with a warning. Repeated starts do not create duplicate icons.

To enable launch at future Windows sign-ins, use `startup-on`; this does not start the helper immediately. Use `startup-off` to remove that entry. Manual start/stop remains available either way. After updating, use `exit` followed by `start` to reload both processes. To uninstall, close active clients and run the installed `setup-scripts/install_keep_awake.py` with `--uninstall` from a separate PowerShell window. It refuses while work is active; modified files, backups, runtime state, logs and the private Python environment are preserved rather than deleted broadly.

## How it works

| Piece | Job |
|---|---|
| [Windows helper](scripts/windows/keep_awake.py) | Tracks live process-owned activity files and requests that Windows remain awake while any covered work remains. Dead process identities are cleaned up. |
| [Tray observer](scripts/windows/joro_watcher/tray.py) | Separately observes the helper's report so its icon survives helper failure. |
| [Event log](scripts/windows/joro_watcher/event_log.py) | Serializes writers and rotation into `~/.joro/keep-awake.log`; up to five files of 1 MiB each, including the current file. Records lifecycle, state changes and errors, not prompts, tool contents or credentials. |
| Claude hooks | Report activity on prompt/tool start. Protection spans permission prompts and Stop-hook continuations; a matching idle notification (normally about a minute later) or session end releases it. |
| [OpenCode plugin](integrations/opencode/index.js) | Tracks new model/compaction work and managed shells. Permission/form waits suspend that foreground contribution without releasing independently running shells. |
| [Local procedure](procedures/keep-awake.md) | Gives agents install, manual controls, startup and uninstall commands. |

The helper and tray are separate processes; closing a client does not close either. Activity files are atomic local records, not a database or network service. Independent work items cannot release one another. Status distinguishes distinct work (`active_count`) from duplicate producer records (`claim_count`). `power_requested` means the native API request was issued—not that every client path or power condition has been proven.

## Limits

- **Modern Standby battery protection is not endurance-verified.** Windows can withdraw system/execution requests on battery. The first coordinated test never started because unplugged-plus-locked conditions were not observed. Do not claim that the watcher guarantees battery or locked-screen operation.
- Claude idle release requires a matching prompt identity. If the client omits that identity, protection stays on conservatively until session end/process exit or manual stop. Permission waits intentionally retain protection.
- Only work observed after the adapters load is covered. OpenCode-managed shells are tracked; detached descendants are not automatically discovered. A monitoring error must be investigated rather than treated as evidence of protection.
- Explicit user sleep, lid-close and critical-battery actions are not overridden. There is no display hold or sleep/hibernate-timeout override.

## Development

```powershell
python -m unittest discover -s tests -p "test_keep_awake*.py" -v
```

Focused checks cover activity ownership, stale notifications, dead/reused processes and preservation/idempotence of hook installation. Earlier exploratory QA maps and probes remain in [qa/](qa/README.md); they are not required to install or use the helper. Real client and native-request evidence is recorded in the [watcher plan](plans/2026-11-11-joro-host-agent-setup/SP-1-agent-keep-awake.md).

## Ownership

Joro manages the host, Infra manages deployed services, Hermod manages repository workflows, and Munnin owns memory contents. Read/output limits, completion sounds, model setup and anchor installation remain separate, later work in the [Council plan](plans/2026-11-11-joro-host-agent-setup/core-plan.md).
