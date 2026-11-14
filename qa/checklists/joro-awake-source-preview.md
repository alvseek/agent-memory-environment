# Joro Awake source preview — QA Checklist

**Source**: [approved source-preview plan](../../plans/2026-11-14-joro-awake-source-preview.md)
**Purpose**: Detect extraction/package omissions and broken installation paths.
**Apps under test**: parent wrapper/builder and child source preview, not the
future no-Python/Store package or battery-endurance behavior.

## Happy path

Download v0.1.0 assets anonymously, compare the ZIP with SHA256SUMS, extract into
a clean directory, run focused tests, then install only in a disposable Windows
account/VM with supported clients. Start/stop/exit and uninstall there.

## Automated coverage

| Item | Automated evidence | Still manual |
|---|---|---|
| Archive completeness/checksum | tests/test_joro_awake_package.py | Real clean-account installation |
| Runtime behavior retained | child test_keep_awake*.py; exact source comparison | Native desktop behavior |
| Release identity | parent verified tagged blobs, download and digest | Future release updates |
| Installer forwarding | --help smoke from wrapper/extraction | Full config write/uninstall in disposable account |

## Checks

- [ ] Automated: focused suites pass and installer --help needs no parent repo.
- [ ] Automated: archive contains installer inputs and notices, not Git/private state.
- [ ] Manual: install in a disposable clean Windows account with a supported Python; confirm unrelated settings preserved.
- [ ] Manual, UI-bound: real covered work changes tray state; actual Exit stops both.
- [ ] Manual: uninstall from disposable account removes owned hooks/plugin/files without deleting unrelated settings.
- [ ] Manual: upgrading an existing source install preserves ownership and startup choices.

## Result

*Not yet run. `/run-qa-test --checklist` writes this section — see its Run record.*
