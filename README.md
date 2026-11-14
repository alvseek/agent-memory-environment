# Joro — Agent Environment

Joro sets up the host an agent works on. Its first capability is **Joro Awake**, a small local Windows keep-awake helper for Claude Code and OpenCode, with a status tray icon and bounded diagnostic log — no MCP server or power-plan edits.

Joro Awake is its own MIT-licensed product repository, [alvseek/joro-awake](https://github.com/alvseek/joro-awake), included here as the `joro-awake/` submodule. This repository owns distribution and the rest of the environment; it keeps no second copy of the implementation.

## Get the checkout

```powershell
git clone --recurse-submodules https://github.com/alvseek/agent-memory-environment.git
```

If the submodule is missing in an existing checkout: `git submodule update --init --recursive`.

## Install and use

Requires Windows, Python 3.12+ and the clients you want to integrate. From this checkout:

```powershell
python setup-scripts/install_keep_awake.py
python "$env:LOCALAPPDATA/Joro/keep-awake/scripts/windows/keep_awake.py" start
python "$env:LOCALAPPDATA/Joro/keep-awake/scripts/windows/keep_awake.py" status
python "$env:LOCALAPPDATA/Joro/keep-awake/scripts/windows/keep_awake.py" stop
```

`setup-scripts/install_keep_awake.py` is a forwarding wrapper: the installer and every file it copies come from the `joro-awake/` submodule. Installation copies the helper locally, creates a private `.venv` with pystray and Pillow for the tray, adds Joro's Claude hooks and OpenCode plugin, and installs a `joro-keep-awake` skill for both clients. The first installation needs internet access to download the tray dependencies. It preserves unrelated Claude hooks and does not edit OpenCode's JSONC configuration. Installation does not start the helper or enable sign-in startup.

Start monitoring before beginning fresh work. Start a new Claude session after installing its hooks. OpenCode discovers the global local plugin automatically; existing in-flight jobs are not retroactively discovered by this first version.

Starting Joro also starts its tray indicator. Zzz means monitoring is idle and sleep is allowed; the eye means a native keep-awake request is active; a warning means monitoring stopped, failed, or cannot confidently read activity. Hover for the reason and active client names. An open client window alone does not mean awake. Windows may initially put the icon in the tray overflow.

`stop` stops monitoring but leaves a warning icon. Use the tray's **Exit**, or the `exit` command, to stop monitoring and remove the icon together. If helper shutdown fails, the tray stays visible with a warning. Repeated starts do not create duplicate icons.

To enable launch at future Windows sign-ins, use `startup-on`; this does not start the helper immediately. Use `startup-off` to remove that entry. Manual start/stop remains available either way. After updating, use `exit` followed by `start` to reload both processes. To uninstall, close active clients and run the installed `setup-scripts/install_keep_awake.py` with `--uninstall` from a separate PowerShell window. It refuses while work is active; modified files, backups, runtime state, logs and the private Python environment are preserved rather than deleted broadly.

The full product documentation, limits and third-party notices live in [joro-awake/README.md](joro-awake/README.md).

## How it works

| Piece | Job |
|---|---|
| [Windows helper](joro-awake/scripts/windows/keep_awake.py) | Tracks live process-owned activity files and requests that Windows remain awake while any covered work remains. Dead process identities are cleaned up. |
| [Tray observer](joro-awake/scripts/windows/joro_watcher/tray.py) | Separately observes the helper's report so its icon survives helper failure. |
| [Event log](joro-awake/scripts/windows/joro_watcher/event_log.py) | Serializes writers and rotation into `~/.joro/keep-awake.log`; up to five files of 1 MiB each, including the current file. Records lifecycle, state changes and errors, not prompts, tool contents or credentials. |
| Claude hooks | Report activity on prompt/tool start. Protection spans permission prompts and Stop-hook continuations; a matching idle notification (normally about a minute later) or session end releases it. |
| [OpenCode plugin](joro-awake/integrations/opencode/index.js) | Tracks new model/compaction work and managed shells. Permission/form waits suspend that foreground contribution without releasing independently running shells. |
| [Local procedure](joro-awake/procedures/keep-awake.md) | Gives agents install, manual controls, startup and uninstall commands. |

The helper and tray are separate processes; closing a client does not close either. Activity files are atomic local records, not a database or network service. Independent work items cannot release one another. `power_requested` means the native API request was issued—not that every client path or power condition has been proven.

## Package a release

```powershell
python setup-scripts/build_joro_awake_package.py
```

This writes the ignored `dist/joro-awake-<version>.zip` and `dist/SHA256SUMS` from the pinned `joro-awake/` submodule. Packaging uses an explicit file allowlist — never a whole-tree zip — and validates that every file the installer copies is present. The archive carries the source, portable focused tests, README, MIT license and verbatim third-party notices; it does not bundle the downloaded tray dependencies or the submodule's Git data. No download endpoint is served from this repository yet.

## Development

```powershell
python -m unittest discover -s joro-awake/tests -p "test_keep_awake*.py" -v
python -m unittest discover -s tests -p "test_*.py" -v
```

The product suite covers activity ownership, stale notifications, dead/reused processes, tray decisions, log retention and installer preservation, using temporary directories only. The environment suite checks the package build. Neither changes installed state.

## Limits

- **Modern Standby battery protection is not endurance-verified.** Do not claim that the watcher guarantees battery or locked-screen operation.
- Only work observed after the adapters load is covered; detached descendants are not discovered automatically. Investigate a monitoring error rather than treating it as protection.
- Explicit sleep, lid-close and critical-battery actions are not overridden. There is no display hold or sleep/hibernate-timeout override.
- Tray menu interaction, tooltip rendering, Explorer restart, future sign-in startup and uninstall remain unverified on this release.

## Ownership

Joro manages the host, Infra manages deployed services, Hermod manages repository workflows, and Munnin owns memory contents. Read/output limits, completion sounds, model setup and anchor installation remain separate, later work in the [Council plan](plans/2026-11-11-joro-host-agent-setup/core-plan.md).
