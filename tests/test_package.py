from __future__ import annotations

import macro_viz


def test_package_version() -> None:
    assert macro_viz.__version__ == "0.1.0.dev0"


def test_public_api_is_intentionally_minimal() -> None:
    assert macro_viz.__all__ == ["__version__"]
