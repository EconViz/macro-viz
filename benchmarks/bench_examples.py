"""Time the example scripts: python startup, imports and each script, best of N.

Not part of the test suite or CI (wall time is machine dependent). Run it by hand, one job at
a time, on a quiet machine::

    uv run python benchmarks/bench_examples.py --runs 5 islm/islm.py panels/five_panel.py

With no script names every script under ``examples/scripts`` except the animations is timed.
The floor row is an empty interpreter and the import of the renderer, which no script can beat.
"""

from __future__ import annotations

import argparse
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "examples" / "scripts"
FLOOR = ("pass", "import mosaickit.rendering.matplotlib.renderer")


def run(command: list[str]) -> tuple[float, float]:
    """Wall and CPU seconds of one child process."""
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    subprocess.run(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wall = time.perf_counter() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return wall, (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)


def best(command: list[str], runs: int) -> tuple[float, float]:
    results = [run(command) for _ in range(runs)]
    return min(r[0] for r in results), min(r[1] for r in results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scripts", nargs="*", help="paths under examples/scripts")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    names = args.scripts or sorted(
        str(p.relative_to(SCRIPTS)) for p in SCRIPTS.glob("*/*.py") if p.parent.name != "animation"
    )
    for code in FLOOR:
        wall, cpu = best([sys.executable, "-c", code], args.runs)
        print(f"{wall:6.2f}s wall {cpu:6.2f}s cpu  floor: python -c {code!r}")
    for name in names:
        output = Path(tempfile.mkdtemp())
        try:
            command = [sys.executable, str(SCRIPTS / name), "--output", str(output)]
            wall, cpu = best(command, args.runs)
        finally:
            shutil.rmtree(output, ignore_errors=True)
        print(f"{wall:6.2f}s wall {cpu:6.2f}s cpu  {name}")


if __name__ == "__main__":
    main()
