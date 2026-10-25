"""IS-LM figures."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas, Layer

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.islm.analysis import ISLMShift, Policy
from macro_viz.islm.models import ISLM
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    THEORY_SIZE,
    curve,
    drop_lines,
    guide,
    marked_point,
    point_name,
    shift_arrow,
    theory_canvas,
    trim,
)

ARROW_SHARE = 0.55
"""Where the shift arrow starts, as a share of the horizontal axis (IS) or of the rate axis."""


def is_curve(model: ISLM, rate_max: float, samples: int) -> list[tuple[float, float]]:
    """Points ``(Y, R)`` of the IS curve for ``R`` from zero to ``rate_max``."""
    step = rate_max / (samples - 1)
    return [(model.is_output(k * step), k * step) for k in range(samples)]


def lm_curve(model: ISLM, rate_max: float, samples: int) -> list[tuple[float, float]]:
    """Points ``(Y, R)`` of the LM curve for ``R`` from zero to ``rate_max``."""
    step = rate_max / (samples - 1)
    return [(model.lm_output(k * step), k * step) for k in range(samples)]


def islm_canvas(
    subject: ISLM | ISLMShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    rate_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    show_crowding: bool = False,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw IS, LM, and their crossing A, optionally after a fiscal or monetary change.

    Given an ``ISLMShift`` the moved curve is thin and dashed, the new crossing is A', and a
    curved arrow shows the shift. ``rate_max`` is the highest interest rate of the curves
    (default: twice the highest equilibrium rate) and ``x_max`` the length of the output axis
    (default ``extent`` times the highest output). With ``show_crowding`` a fiscal change also
    marks ``B``, where the new IS curve stands at the old interest rate: the distance from B to
    A' is the output crowded out.
    """
    shift = subject if isinstance(subject, ISLMShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, ISLM)
    models = [model] + ([shift.post] if shift is not None else [])
    equilibria = [m.equilibrium() for m in models]
    if any(e.rate <= 0 for e in equilibria):
        raise ValidationError("the equilibrium interest rate must be positive to draw the figure")
    rates = rate_max if rate_max is not None else 2.0 * max(e.rate for e in equilibria)
    right = x_max if x_max is not None else extent * max(e.output for e in equilibria)
    top = rates / HEADROOM
    text = Labels(labels)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="islm.axis.output",
        y_label_id="islm.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            trim(is_curve(model, rates, samples), right, top),
            layer_id="macro.islm.is",
            role="macro.curve.primary",
            label=text("islm.curve.is"),
        )
    )
    canvas.extend(
        curve(
            trim(lm_curve(model, rates, samples), right, top),
            layer_id="macro.islm.lm",
            role="macro.curve.secondary",
            label=text("islm.curve.lm"),
        )
    )
    start = equilibria[0]
    point = (start.output, start.rate)
    canvas.extend(
        drop_lines(
            point,
            x_label=text("islm.mark.output"),
            y_label=text("islm.mark.rate"),
            layer_id="macro.islm.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.islm.equilibrium"))
    if shift is not None:
        canvas.extend(_shift_layers(shift, right, top, rates, samples, text, show_crowding))
    return canvas


def _shift_layers(
    shift: ISLMShift,
    right: float,
    top: float,
    rates: float,
    samples: int,
    text: Labels,
    show_crowding: bool,
) -> list[Layer]:
    post, layers = shift.post, []
    if shift.policy is Policy.FISCAL:
        layers += curve(
            trim(is_curve(post, rates, samples), right, top),
            layer_id="macro.islm.is.shifted",
            role="macro.curve.primary.shifted",
            label=text("islm.curve.is_shifted"),
        )
        rate = ARROW_SHARE * rates
        arrow = ((shift.baseline.is_output(rate), rate), (post.is_output(rate), rate))
    else:
        layers += curve(
            trim(lm_curve(post, rates, samples), right, top),
            layer_id="macro.islm.lm.shifted",
            role="macro.curve.secondary.shifted",
            label=text("islm.curve.lm_shifted"),
        )
        rate = ARROW_SHARE * rates
        arrow = ((shift.baseline.lm_output(rate), rate), (post.lm_output(rate), rate))
    layers.append(shift_arrow(*arrow, layer_id="macro.islm.shift", extent=(right, top)))
    end = shift.after
    layers += drop_lines(
        (end.output, end.rate),
        x_label=text("islm.mark.output_shifted"),
        y_label=text("islm.mark.rate_shifted"),
        layer_id="macro.islm.equilibrium.shifted.guide",
    )
    layers += marked_point(
        (end.output, end.rate),
        point_name(0, prime=1),
        layer_id="macro.islm.equilibrium.shifted",
        role="macro.point.shifted",
    )
    if show_crowding and shift.policy is Policy.FISCAL:
        base_rate = shift.before.rate
        b = (post.is_output(base_rate), base_rate)
        layers += marked_point(b, point_name(1), layer_id="macro.islm.crowding")
        layers.append(guide(b, (end.output, end.rate), layer_id="macro.islm.crowding.guide"))
    return layers
