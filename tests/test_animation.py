from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from macro_viz import ValidationError
from macro_viz.animation import frames, linear_values
from macro_viz.keynesian import (
    ConsumptionFunction,
    KeynesianCross,
    analyze_autonomous_shift,
)
from macro_viz.visuals import multiplier_canvas

MODEL = KeynesianCross(ConsumptionFunction(20, 0.6), investment=20, government=30, taxes=20)
LIMIT = 300.0


def builder(amount: float):  # type: ignore[no-untyped-def]
    return multiplier_canvas(analyze_autonomous_shift(MODEL, amount), show_path=False, x_max=LIMIT)


def test_linear_values_include_both_ends() -> None:
    assert linear_values(1.0, 5.0, 5) == (1.0, 2.0, 3.0, 4.0, 5.0)
    with pytest.raises(ValidationError):
        linear_values(0, 1, 1)


def test_frames_are_the_static_builder_at_each_value() -> None:
    canvases = frames(builder, linear_values(10, 30, 3))

    assert len(canvases) == 3
    assert all(canvas.spec.x_max == LIMIT for canvas in canvases)
    assert [layer.id for layer in canvases[0].snapshot().layers] == [
        layer.id for layer in builder(10).snapshot().layers
    ]
    assert canvases[0].snapshot() == builder(10).snapshot()
    assert canvases[0].snapshot() != canvases[2].snapshot()
    with pytest.raises(ValidationError):
        frames(builder, [])


def test_static_figures_work_without_kinetickit() -> None:
    code = textwrap.dedent(
        """
        import sys
        sys.modules["kinetickit"] = None
        sys.modules["glyphkit"] = None
        from macro_viz.keynesian import *
        from macro_viz.visuals import multiplier_canvas
        m = KeynesianCross(ConsumptionFunction(20, 0.6), 20, 30, 20)
        canvas = multiplier_canvas(analyze_autonomous_shift(m, 30))
        assert canvas.snapshot().layers
        import macro_viz.animation as animation
        try:
            animation.save_gif(lambda v: canvas, [1.0, 2.0], "unused.gif")
        except ImportError as error:
            assert "macro-viz[animation]" in str(error)
        else:
            raise SystemExit("expected an ImportError")
        """
    )

    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)


def test_gif_has_one_frame_per_value(tmp_path: Path) -> None:
    pytest.importorskip("kinetickit")
    from PIL import Image

    from macro_viz.animation import save_gif

    target = save_gif(builder, linear_values(10, 30, 4), tmp_path / "out" / "shift.gif", dpi=40)

    with Image.open(target) as image:
        assert getattr(image, "n_frames", 0) == 4


def _font_files() -> list[str]:
    from matplotlib import get_data_path

    root = Path(get_data_path()) / "fonts" / "ttf"
    return [str(root / "DejaVuSerif.ttf"), str(root / "DejaVuSerif-Italic.ttf")]


def test_svg_animates_the_layers_by_their_stable_ids(tmp_path: Path) -> None:
    pytest.importorskip("kinetickit")
    from macro_viz import Config
    from macro_viz.animation import save_svg

    try:
        Config.from_dict({"base": "manual", "fonts": {"serif": _font_files()}}).use()
        target = save_svg(builder, linear_values(10, 30, 3), tmp_path / "out" / "shift.svg")
    finally:
        Config.reset()

    svg = target.read_text(encoding="utf-8")
    assert "<animate" in svg
    for layer_id in (
        "macro.keynesian.demand.shifted",
        "macro.keynesian.equilibrium.shifted.0",
        "macro.keynesian.shift",
    ):
        assert f'data-kk-id="{layer_id}"' in svg


def test_svg_needs_font_files(tmp_path: Path) -> None:
    pytest.importorskip("kinetickit")
    from macro_viz import Config
    from macro_viz.animation import save_svg

    try:
        Config.from_dict({"base": "manual"}).use()
        with pytest.raises(ValidationError, match="font"):
            save_svg(builder, linear_values(10, 30, 2), tmp_path / "x.svg")
    finally:
        Config.reset()
