"""Check that a built wheel carries the web app and every locale file.

Usage: python tools/check_wheel.py dist/cleartake-*.whl
"""

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src/cleartake/web"


def main(wheel: str) -> int:
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    wanted = {f"cleartake/web/{p.relative_to(WEB).as_posix()}" for p in WEB.rglob("*") if p.is_file()}
    wanted |= {"cleartake/cli.py", "cleartake/server.py", "cleartake/pipeline.py"}
    missing = sorted(wanted - names)
    for name in missing:
        print(f"missing from the wheel: {name}")
    print(f"{len(wanted) - len(missing)} of {len(wanted)} expected files are in {Path(wheel).name}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
