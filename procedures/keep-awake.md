---
name: joro-keep-awake
description: Install or control Joro's local Windows keep-awake helper when the user asks to keep the PC awake during Claude Code or OpenCode work, start/stop monitoring, inspect status, configure sign-in startup, or uninstall it.
---

# Joro keep-awake

Use the installed helper, not Windows power-plan edits:

```powershell
& "[JORO-PYTHON]" "[JORO-HELPER]" status
& "[JORO-PYTHON]" "[JORO-HELPER]" start
& "[JORO-PYTHON]" "[JORO-HELPER]" stop
```

Install or refresh the local adapters with:

```powershell
& "[JORO-PYTHON]" "[JORO-INSTALLER]"
```

Only when requested, enable or disable sign-in startup:

```powershell
& "[JORO-PYTHON]" "[JORO-HELPER]" startup-on
& "[JORO-PYTHON]" "[JORO-HELPER]" startup-off
```

Uninstall only when requested, after closing active clients. Run this from a separate PowerShell window; the installer refuses to remove integrations while work is active:

```powershell
& "[JORO-PYTHON]" "[JORO-INSTALLER]" --uninstall
```

Installation does not start the helper or enable startup. Claude hooks apply to newly started sessions; OpenCode discovers the local plugin. Start monitoring before beginning fresh work. Existing in-flight jobs are not retroactively discovered by this small version.

Claude protection spans permission prompts. A Stop hook is not proof of completion, so Claude releases on its idle notification (normally about a minute later, with a matching prompt ID) or session end/process exit. Missing idle identity is handled conservatively: retain protection until session end, or use manual stop. OpenCode tracks new model/compaction work and new managed shells; permission/form waits suspend the foreground contribution, not independently running shells.

`power_requested` reports a native request, not proof that Windows will honor it indefinitely. Modern Standby battery behavior is **not endurance-verified**. Never promise reliable battery/locked-screen protection from status alone. No display hold, power-plan edit, forced lock/sleep, network listener or MCP server is used.
