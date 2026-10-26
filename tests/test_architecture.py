from __future__ import annotations

import ast
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 only
    import tomli as tomllib

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "macro_viz"
DOMAIN_MODULES = (
    "keynesian",
    "adas",
    "money",
    "islm",
    "inflation",
    "growth",
    "dynamics",
    "new_keynesian",
    "graduate",
    "open_economy",
    "transmission",
    "panels",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _imports_matching(path: Path, package: str) -> list[str]:
    return sorted(
        name for name in _imports(path) if name == package or name.startswith(f"{package}.")
    )


def test_macro_viz_never_imports_matplotlib() -> None:
    offenders = {
        path.relative_to(PACKAGE_ROOT): imports
        for path in PACKAGE_ROOT.rglob("*.py")
        if (imports := _imports_matching(path, "matplotlib"))
    }
    assert offenders == {}


def test_economic_domain_does_not_import_mosaickit() -> None:
    roots = (PACKAGE_ROOT / name for name in DOMAIN_MODULES)
    offenders = {
        path.relative_to(PACKAGE_ROOT): imports
        for root in roots
        if root.exists()
        for path in root.rglob("*.py")
        if (imports := _imports_matching(path, "mosaickit"))
    }
    assert offenders == {}


def test_curve_geometry_has_only_the_two_shared_direct_dependencies() -> None:
    project = tomllib.loads((PACKAGE_ROOT.parents[1] / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]

    assert project["dependencies"] == [
        "bezierkit>=1.1.1,<2",
        "mosaickit>=1.0.0rc12,<2",
    ]
