from __future__ import annotations

import macro_viz


def test_package_version() -> None:
    assert macro_viz.__version__ == "0.2.0.dev0"


def test_shared_types_are_available_at_the_package_root() -> None:
    assert macro_viz.__all__ == [
        "Config",
        "LabelPlacementWarning",
        "MacroVizError",
        "ValidationError",
        "__version__",
    ]
