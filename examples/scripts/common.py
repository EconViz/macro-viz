"""Shared helpers for the executable examples.

Every example takes its output folder and settings file from the command line and its
sample data from ``examples/examples.toml``; nothing is written into the scripts.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from macro_viz import Config

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 only
    import tomli as tomllib

EXAMPLES = Path(__file__).resolve().parent.parent
FONT_DIRECTORIES_ENV = "MACRO_VIZ_FONT_DIR"
TEX_FONT_SUBDIRECTORIES = ("fonts/opentype/public/tex-gyre", "fonts/opentype/public/tex-gyre-math")
IMAGE_SUFFIXES = (".svg", ".png", ".gif")
OUTPUT_ROOT = EXAMPLES / "output"

_workspace = tempfile.TemporaryDirectory(prefix="macro-viz-examples-")


def parse_arguments(description: str, argv: Sequence[str] | None = None) -> argparse.Namespace:
    """The command line every example understands."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output folder (default: examples/output/<topic>, the script's folder name)",
    )
    parser.add_argument(
        "--config", type=Path, default=EXAMPLES / "econ-viz.toml", help="settings file"
    )
    parser.add_argument(
        "--data", type=Path, default=EXAMPLES / "examples.toml", help="sample data file"
    )
    parser.add_argument("--suffix", default=".svg", choices=IMAGE_SUFFIXES, help="image format")
    return parser.parse_args(argv)


def font_directories() -> list[Path]:
    """Where font files may live: the environment variable, then a TeX distribution."""
    import os

    found = [
        Path(item) for item in os.environ.get(FONT_DIRECTORIES_ENV, "").split(os.pathsep) if item
    ]
    try:
        root = subprocess.run(
            ["kpsewhich", "-var-value", "TEXMFDIST"], capture_output=True, text=True, check=True
        ).stdout.strip()
        found.extend(Path(root) / relative for relative in TEX_FONT_SUBDIRECTORIES)
    except (OSError, subprocess.CalledProcessError):
        pass
    return [path for path in found if path.is_dir()]


def _font_names(settings: dict[str, Any]) -> list[str]:
    names = list(settings.get("fonts", {}).get("serif", []))
    if "math" in settings.get("font", {}):
        names.append(settings["font"]["math"])
    return names


def load_settings(config: Path) -> Config:
    """Load the settings file, linking its font files beside a copy of it.

    Without every font file the copy drops its font tables, so the example still runs.
    """
    settings = tomllib.loads(config.read_text("utf-8"))
    workspace = Path(_workspace.name)
    available = {
        font.name: font
        for directory in font_directories()
        for font in directory.glob("*.[ot]t[fc]")
    }
    names = _font_names(settings)
    target = workspace / config.name
    if names and all(name in available for name in names):
        for name in names:
            link = workspace / name
            if not link.exists():
                link.symlink_to(available[name])
        shutil.copy(config, target)
    else:
        lines = config.read_text("utf-8").splitlines()
        kept: list[str] = []
        skipping = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("["):
                skipping = stripped in ("[font]", "[fonts]")
            if not skipping:
                kept.append(line)
        target.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return Config.load(target)


def setup(description: str, argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, Path]:
    """Parse arguments, activate the settings, create the output folder."""
    args = parse_arguments(description, argv)
    if args.output is None:
        script = Path(sys._getframe(1).f_globals["__file__"]).resolve()
        args.output = OUTPUT_ROOT / script.parent.name
    load_settings(args.config).use()
    args.output.mkdir(parents=True, exist_ok=True)
    return args, args.output


def load_example(data: Path, name: str) -> dict[str, Any]:
    """The table called ``name`` of the sample data file."""
    table: dict[str, Any] = tomllib.loads(data.read_text("utf-8"))[name]
    return table
