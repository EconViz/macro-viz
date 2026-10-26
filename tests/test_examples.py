from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).parents[1]
SCRIPTS = REPOSITORY_ROOT / "examples" / "scripts"
HELPERS = {"common", "model_common", "panels_common"}


def script_path(name: str) -> Path:
    """The one script called ``name`` in any topic folder, relative to the repository root."""
    (found,) = SCRIPTS.glob(f"*/{name}")
    return found.relative_to(REPOSITORY_ROOT)


def run(script: str, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, str(script_path(script)), *arguments],
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
            str(script_path("keynesian.py")),
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


def _import_script(name: str) -> Any:
    """Import the script called ``name`` from its topic folder, as ``python <path>`` would."""
    import importlib.util

    (path,) = SCRIPTS.glob(f"*/{name}.py") if name not in HELPERS else (SCRIPTS / f"{name}.py",)
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(f"example_{name}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


def test_no_label_overlaps_a_line_or_another_label(tmp_path: Path) -> None:
    """Every example figure is drawn with label placement failures turned into errors."""
    import warnings

    from mosaickit import LayoutWarning

    with warnings.catch_warnings():
        warnings.simplefilter("error", LayoutWarning)
        for name in ("keynesian", "money", "adas", "adas_adjustment", "islm", "growth", "wsps"):
            _import_script(name).main(["--output", str(tmp_path)])


def test_every_example_script_lives_in_a_topic_folder() -> None:
    """The scripts' parent folder names their output topic, so nothing else lists the topics."""
    assert {path.stem for path in SCRIPTS.glob("*.py")} == HELPERS
    folders = [path for path in SCRIPTS.iterdir() if path.is_dir() and path.name != "__pycache__"]
    assert folders
    assert all(any(folder.glob("*.py")) for folder in folders)
    assert not list(SCRIPTS.glob("*/*/*.py"))


@pytest.mark.parametrize(
    ("name", "topic", "image"),
    [
        ("keynesian", "keynesian", "multiplier.svg"),
        ("islm_expectations", "islm", "islm_expected_inflation.svg"),
    ],
)
def test_default_output_is_the_topic_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, topic: str, image: str
) -> None:
    script = _import_script(name)  # imports ``common`` from the scripts folder
    monkeypatch.setattr(sys.modules["common"], "OUTPUT_ROOT", tmp_path)
    script.main([])

    assert (tmp_path / topic / image).stat().st_size > 0
