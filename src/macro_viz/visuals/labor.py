"""Wage-setting and price-setting figures for the natural rate of unemployment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mosaickit import BraceLayer, Canvas, Layer

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.labor.models import WagePriceSetting, WagePriceShift, employment
from macro_viz.visuals._theory import (
    EXTENT,
    HEADROOM,
    THEORY_SIZE,
    axis_mark,
    curve,
    drop_lines,
    marked_point,
    point_name,
    shift_arrow,
    theory_canvas,
    trim,
)

FLOOR_SHARE = 0.12
"""Wage setting stops this share of the wage axis above the horizontal axis."""

RATE_EXTENT = 2.2
"""Default length of the unemployment axis as a multiple of the highest natural rate drawn."""

ARROW_SHARE = 0.25
"""Where along the horizontal axis a shift arrow stands, as a share of its length."""


def _x(model: WagePriceSetting, unemployment: float, labor_force: float | None) -> float:
    del model
    return unemployment if labor_force is None else employment(unemployment, labor_force)


def _line(
    function: object, rate_max: float, labor_force: float | None, right: float
) -> list[tuple[float, float]]:
    """Two end points of a straight curve, ``function`` of the unemployment rate.

    A flat curve (price setting) spans the whole horizontal axis.
    """
    flat = function(0.0) == function(rate_max)  # type: ignore[operator]
    if flat:
        return [(0.0, float(function(0.0))), (right, float(function(0.0)))]  # type: ignore[operator]
    points = [
        (_x(None, u, labor_force), float(function(u)))  # type: ignore[operator, arg-type]
        for u in (0.0, rate_max)
    ]
    return sorted(points)


def wsps_canvas(
    subject: WagePriceSetting | WagePriceShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    labor_force: float | None = None,
    rate_max: float | None = None,
    wage_max: float | None = None,
    extent: float = RATE_EXTENT,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw wage setting, price setting, and the natural rate at their crossing A.

    By default the horizontal axis is the unemployment rate ``u`` (WS falls, PS is flat). With
    ``labor_force`` the axis is employment ``N = L (1 - u)``: WS rises, and braces under the axis
    show employment ``N`` and unemployment ``U`` up to ``L``. Given a ``WagePriceShift`` the
    moved curves are thin and solid, the new crossing is A', and straight arrows show the shifts.
    """
    shift = subject if isinstance(subject, WagePriceShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, WagePriceSetting)
    models = [model] + ([shift.post] if shift is not None else [])
    rates = rate_max if rate_max is not None else extent * max(m.natural_rate() for m in models)
    if rates >= 1:
        raise ValidationError("the unemployment axis must stay below 100 percent")
    wages = wage_max if wage_max is not None else max(m.wage_setting(0.0) for m in models)
    top = wages / HEADROOM
    employment_axis = labor_force is not None
    right = labor_force * 1.0 if employment_axis else rates / HEADROOM  # type: ignore[operator]
    text = Labels(labels)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="labor.axis.employment" if employment_axis else "labor.axis.unemployment",
        y_label_id="labor.axis.wage",
        title=title,
        width=width,
        height=height,
    )

    def curves(m: WagePriceSetting, suffix: str, role: str) -> list[Layer]:
        out: list[Layer] = []
        for name, function in (("ws", m.wage_setting), ("ps", lambda u, m=m: m.price_setting)):
            line = trim(_line(function, rates, labor_force, right), right, top, floor=FLOOR_SHARE)
            moved = suffix and (
                m.ws_scale != model.ws_scale
                or m.ps_scale != model.ps_scale
                or (name == "ws" and m.benefits != model.benefits)
                or (name == "ps" and m.markup != model.markup)
            )
            if suffix and not moved:
                continue
            out += curve(
                line,
                layer_id=f"macro.labor.{name}{suffix}",
                role=f"macro.curve.{'primary' if name == 'ws' else 'secondary'}{role}",
                label=text(f"labor.curve.{name}{'_shifted' if suffix else ''}"),
            )
        return out

    canvas.extend(curves(model, "", ""))
    start = (_x(model, model.natural_rate(), labor_force), model.real_wage())
    canvas.extend(
        drop_lines(
            start,
            x_label=None if employment_axis else text("labor.mark.rate"),
            y_label=text("labor.mark.wage"),
            layer_id="macro.labor.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(start, point_name(0), layer_id="macro.labor.equilibrium"))
    if shift is not None:
        canvas.extend(curves(shift.post, ".shifted", ".shifted"))
        canvas.extend(_shift_layers(shift, right, top, rates, labor_force, text))
    if employment_axis:
        canvas.extend(_braces(models, labor_force, text))  # type: ignore[arg-type]
    return canvas


def _shift_layers(
    shift: WagePriceShift,
    right: float,
    top: float,
    rates: float,
    labor_force: float | None,
    text: Labels,
) -> list[Layer]:
    base, post = shift.baseline, shift.post
    layers: list[Layer] = []
    u = base.natural_rate()
    x = _x(base, u, labor_force)
    start = (x, base.real_wage())
    for name, after, changed in (
        ("ws", post.wage_setting(u), post.wage_setting(u) != base.wage_setting(u)),
        ("ps", post.price_setting, post.price_setting != base.price_setting),
    ):
        if changed:
            layers.append(shift_arrow(start, (x, after), layer_id=f"macro.labor.shift.{name}"))
    end = (_x(post, post.natural_rate(), labor_force), post.real_wage())
    employment_axis = labor_force is not None
    same_rate = abs(shift.after - shift.before) < 1e-12
    layers += drop_lines(
        end,
        x_label=None if employment_axis or same_rate else text("labor.mark.rate_shifted"),
        y_label=None
        if abs(post.real_wage() - base.real_wage()) < 1e-12
        else text("labor.mark.wage_shifted"),
        layer_id="macro.labor.equilibrium.shifted.guide",
    )
    layers += marked_point(
        end,
        point_name(0, prime=1),
        layer_id="macro.labor.equilibrium.shifted",
        role="macro.point.shifted",
    )
    return layers


def _braces(models: Sequence[WagePriceSetting], labor_force: float, text: Labels) -> list[Layer]:
    """Braces on the employment axis: employment up to ``N_n`` and unemployment up to ``L``."""
    natural = employment(models[0].natural_rate(), labor_force)
    return [
        BraceLayer(
            "x",
            0.0,
            natural,
            label=text("labor.mark.employment"),
            side="outside",
            id="macro.labor.brace.employment",
            role="macro.annotation",
        ),
        BraceLayer(
            "x",
            natural,
            labor_force,
            label=text("labor.mark.unemployed"),
            side="outside",
            id="macro.labor.brace.unemployment",
            role="macro.annotation",
        ),
        axis_mark(
            "x",
            labor_force,
            text("labor.mark.labor_force"),
            layer_id="macro.labor.labor_force.mark",
        ),
    ]


__all__ = ["wsps_canvas"]
del EXTENT
