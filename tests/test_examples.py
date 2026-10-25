from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def run(script: str, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, f"examples/scripts/{script}", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_examples_write_nonempty_images(tmp_path: Path) -> None:
    run("keynesian.py", "--output", str(tmp_path))
    run("keynesian_animation.py", "--output", str(tmp_path))
    run("money.py", "--output", str(tmp_path))
    run("money_animation.py", "--output", str(tmp_path))
    run("adas.py", "--output", str(tmp_path))
    run("adas_animation.py", "--output", str(tmp_path))

    images = {image.stem: image for image in tmp_path.glob("*.svg")}
    assert {
        "keynesian_cross",
        "keynesian_cross_curved",
        "multiplier",
        "consumption_function",
        "money_demand",
        "money_market",
        "money_income_shift",
        "money_supply_shift",
        "aggregate_supply",
        "aggregate_supply_shift",
        "aggregate_demand_shifts",
        "adas_equilibrium",
        "adas_employment",
        "adas_productivity",
        "adas_demand_shock",
    } <= set(images)
    assert all(image.stat().st_size > 0 for image in images.values())


def test_example_output_follows_the_arguments(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "examples/scripts/keynesian.py",
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

    assert (tmp_path / "nested" / "multiplier.png").stat().st_size > 0
