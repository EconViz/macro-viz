"""The golden-rule figure."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas

from macro_viz.core.errors import ValidationError
from macro_viz.core.i18n import Labels
from macro_viz.growth.models import Solow
from macro_viz.growth.visuals._preset import GOLDEN_SAMPLES_FLOOR
from macro_viz.growth.visuals.steady_state import _ids
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    HEADROOM,
    THEORY_SIZE,
    curve,
    drop_lines,
    marked_point,
    point_name,
    sample,
    theory_canvas,
)


def golden_rule_canvas(
    model: Solow,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    effective: bool = False,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw steady-state consumption per worker against the saving rate, with its maximum.

    The hump peaks at the golden-rule saving rate ``s_G``, marked on the saving axis.
    """
    prefix, text = _ids(effective), Labels(labels)
    golden = model.golden_rule_saving()
    if not 0 < golden < 1:
        raise ValidationError("the golden-rule saving rate must lie between 0 and 1")
    points = sample(model.consumption_at, GOLDEN_SAMPLES_FLOOR, 1 - GOLDEN_SAMPLES_FLOOR, samples)
    peak = model.consumption_at(golden)
    top = peak / HEADROOM
    canvas = theory_canvas(
        1.0,
        top,
        labels=text,
        x_label_id=f"{prefix}axis.saving",
        y_label_id=f"{prefix}axis.consumption",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            points,
            layer_id="macro.growth.consumption",
            role="macro.curve.primary",
            label=text(f"{prefix}curve.consumption"),
        )
    )
    canvas.extend(
        drop_lines(
            (golden, peak),
            x_label=text(f"{prefix}mark.golden"),
            y_label=None,
            layer_id="macro.growth.golden.guide",
        )
    )
    canvas.extend(marked_point((golden, peak), point_name(0), layer_id="macro.growth.golden"))
    return canvas
