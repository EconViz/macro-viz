"""The open-economy goods market: the cross with net exports."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas

from macro_viz.i18n import Labels
from macro_viz.open_economy.models import OpenEconomy, OpenEconomyShift
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    axis_mark,
    curve,
    drop_lines,
    guide,
    marked_point,
    point_name,
    sample,
    shift_arrow,
    theory_canvas,
    trim,
)
from macro_viz.visuals.keynesian._base import _base_layers
from macro_viz.visuals.keynesian.cross import keynesian_cross_canvas


def open_goods_canvas(
    subject: OpenEconomy | OpenEconomyShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    show_balanced_trade: bool = True,
    **options: object,
) -> Canvas:
    """Draw the open-economy goods market: the 45-degree line, demand, and equilibrium A.

    Given an ``OpenEconomyShift`` the new demand line is thin and solid with its crossing A'.
    ``show_balanced_trade`` adds a dotted vertical at the output where net exports are zero:
    A to its left means a trade surplus, to its right a trade deficit.
    """
    shift = subject if isinstance(subject, OpenEconomyShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, OpenEconomy)
    if shift is None:
        canvas = keynesian_cross_canvas(model, title=title, labels=labels, **options)  # type: ignore[arg-type]
    else:
        canvas = _open_shift(shift, title, labels, options)
    if show_balanced_trade and model.import_propensity > 0:
        limit = canvas.spec.x_max
        balanced = model.balanced_trade_output()
        if balanced < limit * HEADROOM:
            text = Labels(labels)
            canvas.add(guide((balanced, 0.0), (balanced, balanced), layer_id="macro.open.balanced"))
            canvas.add(
                axis_mark(
                    "x", balanced, text("open.mark.balanced"), layer_id="macro.open.balanced.mark"
                )
            )
    return canvas


def _open_shift(
    shift: OpenEconomyShift,
    title: str | None,
    labels: Mapping[str, str] | None,
    options: Mapping[str, object],
) -> Canvas:
    baseline, post = shift.baseline, shift.post
    limit = options.get("x_max")
    extent = float(options.get("extent", EXTENT))  # type: ignore[arg-type]
    samples = int(options.get("samples", DEFAULT_SAMPLES))  # type: ignore[call-overload]
    right = (
        float(limit)  # type: ignore[arg-type]
        if limit is not None
        else extent * max(baseline.equilibrium().output, post.equilibrium().output)
    )
    text = Labels(labels)
    canvas = theory_canvas(
        right,
        right,
        labels=text,
        x_label_id="keynesian.axis.income",
        y_label_id="keynesian.axis.demand",
        title=title,
    )
    canvas.extend(_base_layers(baseline, right, text, samples))
    canvas.extend(
        curve(
            trim(sample(post.demand, 0.0, right, samples), right, right),
            layer_id="macro.keynesian.demand.shifted",
            role="macro.curve.primary.shifted",
            label=text("keynesian.curve.demand_shifted"),
        )
    )
    for index, (m, name, role) in enumerate(
        (
            (baseline, "macro.keynesian.equilibrium", "macro.point"),
            (post, "macro.keynesian.equilibrium.shifted", "macro.point.shifted"),
        )
    ):
        e = m.equilibrium()
        point = (e.output, e.demand)
        canvas.extend(
            drop_lines(
                point,
                x_label=text(
                    "keynesian.mark.output" if index == 0 else "keynesian.mark.output_shifted"
                ),
                y_label=text(
                    "keynesian.mark.output" if index == 0 else "keynesian.mark.output_shifted"
                ),
                layer_id=f"{name}.guide",
            )
        )
        canvas.extend(marked_point(point, point_name(0, prime=index), layer_id=name, role=role))
    old = baseline.equilibrium()
    canvas.add(
        shift_arrow(
            (old.output, old.demand),
            (old.output, post.demand(old.output)),
            layer_id="macro.keynesian.shift",
        )
    )
    return canvas
