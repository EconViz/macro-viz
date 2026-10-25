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
    run("islm.py", "--output", str(tmp_path))
    run("islm_animation.py", "--output", str(tmp_path))
    run("growth.py", "--output", str(tmp_path))
    run("growth_animation.py", "--output", str(tmp_path))
    run("wsps.py", "--output", str(tmp_path))
    run("liquidity_trap.py", "--output", str(tmp_path))

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
        "islm",
        "wsps",
        "money_zero_bound",
        "islm_zero_bound",
        "wsps_employment",
        "solow",
        "golden_rule",
        "production_function",
        "solow_level_path",
        "solow_log_path",
        "islm_crowding_out",
        "islm_monetary_expansion",
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


def test_no_label_overlaps_a_line_or_another_label(tmp_path: Path) -> None:
    """Every example figure is drawn with label placement failures turned into errors."""
    import importlib
    import warnings

    from mosaickit import LayoutWarning

    scripts = str(REPOSITORY_ROOT / "examples" / "scripts")
    sys.path.insert(0, scripts)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", LayoutWarning)
            for name in ("keynesian", "money", "adas", "adas_adjustment", "islm", "growth", "wsps"):
                importlib.import_module(name).main(["--output", str(tmp_path)])
    finally:
        sys.path.remove(scripts)
