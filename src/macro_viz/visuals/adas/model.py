"""The AD-AS figure of a model or of a shift in one of its curves."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import AxisNoteLayer, Canvas, Layer, TextLayer

from macro_viz.adas.analysis import ASADShift, Shock
from macro_viz.adas.models import ASADModel
from macro_viz.i18n import Labels
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    THEORY_SIZE,
    axis_mark,
    curve,
    drop_lines,
    guide,
    marked_point,
    movement,
    point_name,
    shift_arrow,
    theory_canvas,
)
from macro_viz.visuals.adas._curves import _scale, demand_curve, supply_curve
from macro_viz.visuals.adas._preset import AMBIGUOUS_SPAN_SHARE, LABEL_GAP, SHIFT_ARROW_SHARE


def adas_canvas(
    subject: ASADModel | ASADShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    y_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    show_natural_output: bool = True,
    productivity: float | None = None,
    ambiguous_demand: bool = False,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw aggregate supply and demand, their crossing A, and optionally a shock.

    ``show_natural_output`` adds the dashed vertical at ``Yn``, the point ``B = (Yn, Pe)`` on AS,
    and the mark ``Pe``. Given an ``ASADShift`` the moved curve is thin and solid and the new
    crossing is A'. ``productivity`` (the level ``A`` of ``N = Y / A``) names the employment
    that goes with equilibrium output below the axis. ``ambiguous_demand`` marks the unknown
    direction of a demand shift with two arrows and question marks.
    """
    shift = subject if isinstance(subject, ASADShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, ASADModel)
    models = [model] + ([shift.post] if shift is not None else [])
    right, top = _scale(models, x_max, y_max, extent)
    text = Labels(labels)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=title,
        width=width,
        height=height,
    )
    equilibrium = model.equilibrium()
    canvas.extend(
        curve(
            supply_curve(model.supply, right, top, samples),
            layer_id="macro.adas.supply",
            role="macro.curve.secondary",
            label=text("adas.curve.supply"),
        )
    )
    canvas.extend(
        curve(
            demand_curve(model.demand, right, top, samples),
            layer_id="macro.adas.demand",
            role="macro.curve.primary",
            label=text("adas.curve.demand"),
        )
    )
    if show_natural_output:
        canvas.extend(_natural_layers(model, right, top, text))
    point = (equilibrium.output, equilibrium.price)
    canvas.extend(
        drop_lines(
            point,
            x_label=text("adas.mark.output"),
            y_label=text("adas.mark.price"),
            layer_id="macro.adas.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.adas.equilibrium"))
    if productivity is not None:
        canvas.add(
            AxisNoteLayer(
                "x",
                equilibrium.output,
                text("adas.note.employment"),
                id="macro.adas.employment",
                role="macro.annotation",
            )
        )
    if shift is not None:
        canvas.extend(_shift_layers(shift, right, top, samples, text, ambiguous_demand))
    return canvas


def _natural_layers(model: ASADModel, right: float, top: float, text: Labels) -> list[Layer]:
    equilibrium = model.equilibrium()
    natural, expected = equilibrium.natural_output, equilibrium.expected_price
    anchor = (natural, model.supply.price(natural))
    layers: list[Layer] = [
        guide((natural, 0.0), (natural, HEADROOM * top), layer_id="macro.adas.natural"),
        axis_mark(
            "x", natural, text("adas.mark.natural_output"), layer_id="macro.adas.natural.mark"
        ),
    ]
    if abs(anchor[1] - expected) < expected * 1e-9:
        layers += drop_lines(
            anchor,
            x_label=None,
            y_label=text("adas.mark.expected_price"),
            layer_id="macro.adas.expected",
        )
        layers += marked_point(anchor, point_name(1), layer_id="macro.adas.anchor")
    return layers


def _shift_layers(
    shift: ASADShift,
    right: float,
    top: float,
    samples: int,
    text: Labels,
    ambiguous: bool,
) -> list[Layer]:
    layers: list[Layer] = []
    post = shift.post
    if shift.shock is Shock.SUPPLY:
        layers += curve(
            supply_curve(post.supply, right, top, samples),
            layer_id="macro.adas.supply.shifted",
            role="macro.curve.secondary.shifted",
            label=text("adas.curve.supply_shifted"),
        )
        old = shift.baseline.equilibrium()
        layers.append(
            shift_arrow(
                (old.output, old.price),
                (old.output, post.supply.price(old.output)),
                layer_id="macro.adas.shift",
            )
        )
    else:
        layers += curve(
            demand_curve(post.demand, right, top, samples),
            layer_id="macro.adas.demand.shifted",
            role="macro.curve.primary.shifted",
            label=text("adas.curve.demand_shifted"),
        )
        old = shift.baseline.equilibrium()
        layers.append(
            shift_arrow(
                (old.output, old.price),
                (post.demand.output(old.price), old.price),
                layer_id="macro.adas.shift",
            )
        )
    if ambiguous:
        layers += _ambiguous_layers(shift, right, top, text)
    end = post.equilibrium()
    point = (end.output, end.price)
    layers += drop_lines(
        point,
        x_label=text("adas.mark.output_shifted"),
        y_label=text("adas.mark.price_shifted"),
        layer_id="macro.adas.equilibrium.shifted.guide",
    )
    layers += marked_point(
        point,
        point_name(0, prime=1),
        layer_id="macro.adas.equilibrium.shifted",
        role="macro.point.shifted",
    )
    return layers


def _ambiguous_layers(shift: ASADShift, right: float, top: float, text: Labels) -> list[Layer]:
    """Two arrows from the demand curve, left and right, each marked with a question mark."""
    level = SHIFT_ARROW_SHARE * top
    start = shift.baseline.demand.output(level)
    span = AMBIGUOUS_SPAN_SHARE * right
    layers: list[Layer] = []
    for name, sign in (("left", -1), ("right", 1)):
        end = (start + sign * span, level)
        layers.append(movement((start, level), end, layer_id=f"macro.adas.ambiguous.{name}"))
        layers.append(
            TextLayer(
                end,
                text("adas.mark.ambiguous"),
                id=f"macro.adas.ambiguous.{name}.label",
                role="macro.annotation",
                anchor="bottom",
                offset=(0, LABEL_GAP),
            )
        )
    return layers
