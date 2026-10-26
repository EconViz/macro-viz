from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

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
    run("open_asad.py", "--output", str(tmp_path))
    run("mundell_fleming.py", "--output", str(tmp_path))
    run("open_economy.py", "--output", str(tmp_path))
    run("islm_expectations.py", "--output", str(tmp_path))
    run("central_bank_money.py", "--output", str(tmp_path))
    run("liquidity_trap.py", "--output", str(tmp_path))
    run("transmission.py", "--output", str(tmp_path))

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
        "open_asad_devaluation",
        "interest_parity",
        "open_islm_fiscal",
        "open_goods",
        "open_fiscal_expansion",
        "islm_expected_inflation",
        "central_bank_money",
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
        "is_derivation",
        "lm_derivation",
        "ad_derivation",
        "as_derivation",
        "islm_standalone",
        "adas_standalone",
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


def _import_script(name: str) -> object:
    import importlib

    scripts = str(REPOSITORY_ROOT / "examples" / "scripts")
    sys.path.insert(0, scripts)
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(scripts)


def test_every_example_script_has_an_output_topic() -> None:
    scripts = REPOSITORY_ROOT / "examples" / "scripts"
    runnable = {path.stem for path in scripts.glob("*.py")} - {"common", "panels_common"}

    assert set(_import_script("common").TOPICS) == runnable  # type: ignore[attr-defined]


def test_default_output_is_the_topic_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_import_script("common"), "OUTPUT_ROOT", tmp_path)
    _import_script("keynesian").main([])  # type: ignore[attr-defined]

    assert (tmp_path / "keynesian" / "multiplier.svg").stat().st_size > 0
