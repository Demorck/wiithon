#!/usr/bin/env python3
"""
Regenerate the autodoc module pages under docs/sphinx/source/api.

Package pages (wiithon.rst, wiithon.disc.rst, ...) are written by hand and are
never touched. Only leaf module pages are generated.

    python docs/regen_api.py           sync the api directory
    python docs/regen_api.py --check   report drift and exit 1, for CI
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PACKAGE = SRC / "wiithon"
API_DIR = ROOT / "docs" / "sphinx" / "source" / "api"

EXCLUDE = [PACKAGE / "cli.py", PACKAGE / "helpers"]


def is_package_page(name: str) -> bool:
    """True when <name>.rst documents a package, which we own by hand."""
    return (SRC / Path(*name.split("."))).is_dir()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def generate(dest: Path) -> None:
    subprocess.run(
        [
            sys.executable, "-m", "sphinx.ext.apidoc",
            "-o", str(dest), "-f", "-e", "-M", "-T",
            str(PACKAGE), *(str(p) for p in EXCLUDE),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report drift instead of applying it")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        fresh = {p.stem: p for p in Path(tmp).glob("*.rst")
                 if not is_package_page(p.stem)}

        if not fresh:
            print("sphinx-apidoc produced no module pages, aborting.", file=sys.stderr)
            return 2


        current = {p.stem: p for p in API_DIR.glob("*.rst")
                   if not is_package_page(p.stem)}

        added = sorted(fresh.keys() - current.keys())
        removed = sorted(current.keys() - fresh.keys())
        outdated = sorted(n for n in fresh.keys() & current.keys()
                          if read(fresh[n]) != read(current[n]))

        if args.check:
            if not (added or removed or outdated):
                print("api/ is up to date.")
                return 0

            for name in added:
                print(f"missing:  api/{name}.rst")
            for name in removed:
                print(f"stale:    api/{name}.rst")
            for name in outdated:
                print(f"outdated: api/{name}.rst")

            print("\nRun 'python docs/regen_api.py' and commit the result.")
            return 1

        for name in added + outdated:
            shutil.copyfile(fresh[name], API_DIR / f"{name}.rst")
        for name in removed:
            (API_DIR / f"{name}.rst").unlink()

        print(f"{len(added)} added, {len(outdated)} updated, {len(removed)} removed.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())