"""IS-LM figures."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from mosaickit import BraceLayer, Canvas, Layer

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.islm.analysis import ISLMShift, Policy
from macro_viz.islm.models import ISLM, ISLMExpectations
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

SAME_VALUE = 1e-9
"""Two values closer than this share one mark on the axis."""

ZERO_RATE_SHARE = 0.5
"""When the equilibrium rate is zero, the rate axis is this share of the rate at which IS meets
the output axis."""

ARROW_SHARE = 0.55
"""Where the shift arrow starts, as a share of the horizontal axis (IS) or of the rate axis."""


def is_curve(model: ISLM, rate_max: float, samples: int) -> list[tuple[float, float]]:
    """Points ``(Y, R)`` of the IS curve for ``R`` from zero to ``rate_max``."""
    step = rate_max / (samples - 1)
    return [(model.is_output(k * step), k * step) for k in range(samples)]


def lm_curve(model: ISLM, rate_max: float, samples: int) -> list[tuple[float, float]]:
    """Points ``(Y, R)`` of the LM curve for ``R`` from zero to ``rate_max``."""
    step = rate_max / (samples - 1)
    points = [(model.lm_output(k * step), k * step) for k in range(samples)]
    if model.zero_bound:
        # flat at a zero rate up to the output where money demand reaches zero interest
        points.insert(0, (0.0, 0.0))
    return points


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

    Given an ``ISLMShift`` the moved curve is thin and solid, the new crossing is A', and a
    straight arrow shows the shift. ``rate_max`` is the highest interest rate of the curves
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
    if any(
        e.rate < 0 or (e.rate == 0 and not m.zero_bound)
        for e, m in zip(equilibria, models, strict=True)
    ):
        raise ValidationError("the equilibrium interest rate must be positive to draw the figure")
    highest = max(e.rate for e in equilibria)
    fallback = ZERO_RATE_SHARE * model.autonomous / model.sensitivity
    rates = rate_max if rate_max is not None else (2.0 * highest if highest > 0 else fallback)
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
            y_label=text("islm.mark.rate") if start.rate > 0 else None,
            layer_id="macro.islm.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.islm.equilibrium"))
    if shift is not None:
        canvas.extend(_shift_layers(shift, right, top, rates, samples, text, show_crowding))
    return canvas


def _arrow(
    shift: ISLMShift,
    rates: float,
    old_output: Callable[[float], float],
    new_output: Callable[[float], float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """A horizontal arrow from the old crossing to the moved curve, at the old crossing's rate.

    When the old rate is zero the arrow would run along the axis, so it is drawn at
    ``ARROW_SHARE`` of the highest rate, from the old curve.
    """
    before = shift.before
    if before.rate > 0:
        return (before.output, before.rate), (new_output(before.rate), before.rate)
    rate = ARROW_SHARE * rates
    return (old_output(rate), rate), (new_output(rate), rate)


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
        arrow = _arrow(shift, rates, shift.baseline.is_output, post.is_output)
    else:
        layers += curve(
            trim(lm_curve(post, rates, samples), right, top),
            layer_id="macro.islm.lm.shifted",
            role="macro.curve.secondary.shifted",
            label=text("islm.curve.lm_shifted"),
        )
        arrow = _arrow(shift, rates, shift.baseline.lm_output, post.lm_output)
    layers.append(shift_arrow(*arrow, layer_id="macro.islm.shift"))
    end = shift.after
    unchanged = (
        abs(end.output - shift.before.output) < SAME_VALUE
        and abs(end.rate - shift.before.rate) < SAME_VALUE
    )
    if not unchanged:
        layers += drop_lines(
            (end.output, end.rate),
            x_label=None
            if abs(end.output - shift.before.output) < SAME_VALUE
            else text("islm.mark.output_shifted"),
            y_label=text("islm.mark.rate_shifted") if end.rate > 0 else None,
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


def islm_expectations_canvas(
    subject: ISLMExpectations,
    *,
    after: ISLMExpectations | None = None,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    **options: object,
) -> Canvas:
    """Draw IS-LM against the nominal rate with the real rate as a gap below it.

    A brace on the rate axis spans from the real rate ``r`` up to the nominal rate ``i`` at the
    equilibrium output and is named ``pi^e``. With ``after`` (changed expectations or money) the
    new crossing and curves are drawn as in ``islm_canvas``; the nominal rate is on the axis.
    """
    text = Labels(labels)
    overrides = {
        "islm.axis.rate": text("islm.axis.nominal_rate"),
        "islm.mark.rate": text("islm.mark.nominal_rate"),
        "islm.mark.rate_shifted": text("islm.mark.nominal_rate_shifted"),
    }
    overrides.update(dict(labels or {}))
    base = subject.nominal_model()
    if after is None:
        canvas = islm_canvas(base, title=title, labels=overrides, **options)  # type: ignore[arg-type]
    else:
        from macro_viz.direction import Direction
        from macro_viz.islm.analysis import ISLMShift, Policy

        post = after.nominal_model()
        before_e, after_e = base.equilibrium(), post.equilibrium()
        shift = ISLMShift(
            base,
            post,
            Policy.FISCAL if post.autonomous != base.autonomous else Policy.MONETARY,
            Direction.of(after_e.output - before_e.output),
            Direction.of(after_e.rate - before_e.rate),
        )
        canvas = islm_canvas(shift, title=title, labels=overrides, **options)  # type: ignore[arg-type]
    equilibrium = subject.equilibrium()
    canvas.add(
        BraceLayer(
            "y",
            subject.real_rate,
            equilibrium.rate,
            label=text("islm.mark.expected_inflation"),
            side="outside",
            id="macro.islm.wedge",
            role="macro.annotation",
        )
    )
    return canvas
