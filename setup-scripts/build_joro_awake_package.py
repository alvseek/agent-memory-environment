"""Build the versioned Joro Awake source ZIP and SHA-256 checksum.

The joro-awake submodule owns the implementation; this repository only packages
it. The file allowlist is explicit so a package can never include the
submodule's .git directory, caches or a developer's local environment.
"""

import argparse
import hashlib
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO / "joro-awake"
DEFAULT_DIST = REPO / "dist"

FILES = (
    ".gitattributes",
    ".gitignore",
    "LICENSE",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "VERSION",
    "licenses/Pillow-LICENSE",
    "licenses/pystray-COPYING",
    "licenses/pystray-COPYING.LGPL",
    "licenses/six-LICENSE",
    "integrations/opencode/index.js",
    "procedures/keep-awake.md",
    "scripts/windows/keep_awake.py",
    "scripts/windows/joro_watcher/__init__.py",
    "scripts/windows/joro_watcher/event_log.py",
    "scripts/windows/joro_watcher/power.py",
    "scripts/windows/joro_watcher/tray.py",
    "setup-scripts/install_keep_awake.py",
    "tests/test_keep_awake.py",
    "tests/test_keep_awake_filesystem.py",
    "tests/test_keep_awake_installer.py",
    "tests/test_keep_awake_tray.py",
)


def version(source):
    return (source / "VERSION").read_text(encoding="utf-8").strip()


def build(source=DEFAULT_SOURCE, dist=DEFAULT_DIST):
    """Write <dist>/joro-awake-<version>.zip and SHA256SUMS; return both paths and the digest."""
    source, dist = Path(source), Path(dist)
    missing = [name for name in FILES if not (source / name).is_file()]
    if missing:
        raise SystemExit("Joro Awake source is incomplete: " + ", ".join(missing))
    release = version(source)
    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / f"joro-awake-{release}.zip"
    prefix = f"joro-awake-{release}"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            bundle.write(source / name, f"{prefix}/{name}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sums = dist / "SHA256SUMS"
    sums.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return archive, sums, digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    args = parser.parse_args()
    archive, sums, digest = build(args.source, args.dist)
    print(f"{archive}\n{sums}\nsha256 {digest}")
