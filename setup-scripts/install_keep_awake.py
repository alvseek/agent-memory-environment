"""Forward to the Joro Awake installer owned by the joro-awake submodule."""

import runpy
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "joro-awake/setup-scripts/install_keep_awake.py"

if not INSTALLER.exists():
    raise SystemExit("The joro-awake submodule is missing; run: git submodule update --init --recursive")

runpy.run_path(str(INSTALLER), run_name="__main__")
