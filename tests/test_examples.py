from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_all_examples_execute_and_write_nonempty_images(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "examples/scripts/run_all.py", "--output", str(tmp_path)],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    images = tuple(tmp_path.glob("*.svg"))
    assert len(images) == 9
    assert all(image.stat().st_size > 0 for image in images)


def test_example_output_follows_the_arguments(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "examples/scripts/gdp_components.py",
            "--output",
            str(tmp_path / "nested"),
            "--suffix",
            ".png",
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (tmp_path / "nested" / "gdp_components.png").stat().st_size > 0
