"""The production function and the Solow steady state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mosaickit import ArrowLayer, Canvas, Layer

from macro_viz.growth.analysis import SteadyStateShift
from macro_viz.growth.models import Solow
from macro_viz.i18n import Labels
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    THEORY_SIZE,
    curve,
    drop_lines,
    marked_point,
    point_name,
    sample,
    shift_arrow,
    theory_canvas,
    trim,
)
from macro_viz.visuals.growth._preset import (
    CONVERGENCE_HEIGHT_SHARE,
    CONVERGENCE_SPAN_SHARE,
    SOLOW_EXTENT,
)


def _ids(effective: bool) -> str:
    return "solow.effective." if effective else "solow."


def _limits(
    models: Sequence[Solow], k_max: float | None, y_max: float | None, extent: float
) -> tuple[float, float]:
    right = k_max if k_max is not None else extent * max(m.steady_state() for m in models)
    top = y_max if y_max is not None else max(m.output(right) for m in models) / HEADROOM
    return right, top


def production_function_canvas(
    model: Solow,
    *,
    shifted: Solow | None = None,
    points: Sequence[float] = (),
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    effective: bool = False,
    k_max: float | None = None,
    y_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw the concave production function with points at the given capital levels.

    Each capital level in ``points`` gets a dot named A, B, ... with guides to both axes; with
    ``shifted`` (better technology, another function) the new curve is thin and solid and a
    curved arrow shows the upward shift.
    """
    prefix, text = _ids(effective), Labels(labels)
    models = [model] + ([shifted] if shifted is not None else [])
    right, top = _limits(models, k_max, y_max, extent)
    if shifted is not None and y_max is None:
        top = max(m.output(right) for m in models) / HEADROOM
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id=f"{prefix}axis.capital",
        y_label_id=f"{prefix}axis.output",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            trim(sample(model.output, 0.0, right, samples), right, top),
            layer_id="macro.growth.production",
            role="macro.curve.primary",
            label=text(f"{prefix}curve.production"),
        )
    )
    for index, capital in enumerate(points):
        point = (capital, model.output(capital))
        canvas.extend(
            drop_lines(
                point,
                x_label=None,
                y_label=None,
                layer_id=f"macro.growth.point.{index}.guide",
            )
        )
        canvas.extend(
            marked_point(point, point_name(index), layer_id=f"macro.growth.point.{index}")
        )
    if shifted is not None:
        canvas.extend(
            curve(
                trim(sample(shifted.output, 0.0, right, samples), right, top),
                layer_id="macro.growth.production.shifted",
                role="macro.curve.primary.shifted",
                label=text(f"{prefix}curve.production_shifted"),
            )
        )
        x = points[0] if points else 0.5 * right
        canvas.add(
            shift_arrow((x, model.output(x)), (x, shifted.output(x)), layer_id="macro.growth.shift")
        )
    return canvas


def solow_canvas(
    subject: Solow | SteadyStateShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    effective: bool = False,
    show_production: bool = True,
    show_convergence: bool = True,
    k_max: float | None = None,
    y_max: float | None = None,
    extent: float = SOLOW_EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw output, saving ``s f(k)``, and required investment, with the steady state A.

    Given a ``SteadyStateShift`` (a change of the saving rate, population or technology growth)
    the changed curve is thin and solid, the new steady state is A', and a straight arrow shows
    the shift. Arrows along the capital axis point toward each steady state.
    """
    shift = subject if isinstance(subject, SteadyStateShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, Solow)
    models = [model] + ([shift.post] if shift is not None else [])
    right, top = _limits(models, k_max, y_max, extent)
    prefix, text = _ids(effective), Labels(labels)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id=f"{prefix}axis.capital",
        y_label_id=f"{prefix}axis.output",
        title=title,
        width=width,
        height=height,
    )
    if show_production:
        canvas.extend(
            curve(
                trim(sample(model.output, 0.0, right, samples), right, top),
                layer_id="macro.growth.production",
                role="macro.curve.primary",
                label=text(f"{prefix}curve.production"),
            )
        )
    canvas.extend(
        curve(
            trim(sample(model.investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.investment",
            role="macro.curve.secondary",
            label=text(f"{prefix}curve.investment"),
        )
    )
    canvas.extend(
        curve(
            trim(sample(model.required_investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.required",
            role="macro.curve.secondary",
            label=text(f"{prefix}curve.required"),
        )
    )
    steady = model.steady_state()
    point = (steady, model.investment(steady))
    canvas.extend(
        drop_lines(
            point,
            x_label=text(f"{prefix}mark.capital"),
            y_label=None,
            layer_id="macro.growth.steady.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.growth.steady"))
    if show_convergence:
        canvas.extend(_convergence(steady, right, top, "macro.growth.convergence"))
    if shift is not None:
        canvas.extend(_shift_layers(shift, right, top, samples, text, prefix, show_convergence))
    return canvas


def _convergence(steady: float, right: float, top: float, layer_id: str) -> list[Layer]:
    """Two arrows along the capital axis, one from each side, pointing at ``steady``."""
    height = CONVERGENCE_HEIGHT_SHARE * top
    span = CONVERGENCE_SPAN_SHARE * right
    return [
        ArrowLayer(
            (steady - 2 * span, height),
            (steady - 0.25 * span, height),
            id=f"{layer_id}.left",
            role="macro.movement",
            z_index=5,
        ),
        ArrowLayer(
            (steady + 2 * span, height),
            (steady + 0.25 * span, height),
            id=f"{layer_id}.right",
            role="macro.movement",
            z_index=5,
        ),
    ]


def _shift_layers(
    shift: SteadyStateShift,
    right: float,
    top: float,
    samples: int,
    text: Labels,
    prefix: str,
    convergence: bool,
) -> list[Layer]:
    post, base = shift.post, shift.baseline
    layers: list[Layer] = []
    x = base.steady_state()
    if post.saving != base.saving:
        layers += curve(
            trim(sample(post.investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.investment.shifted",
            role="macro.curve.secondary.shifted",
            label=text(f"{prefix}curve.investment_shifted"),
        )
        layers.append(
            shift_arrow(
                (x, base.investment(x)), (x, post.investment(x)), layer_id="macro.growth.shift"
            )
        )
    else:
        layers += curve(
            trim(sample(post.required_investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.required.shifted",
            role="macro.curve.secondary.shifted",
            label=text(f"{prefix}curve.required_shifted"),
        )
        layers.append(
            shift_arrow(
                (x, base.required_investment(x)),
                (x, post.required_investment(x)),
                layer_id="macro.growth.shift",
            )
        )
    steady = post.steady_state()
    point = (steady, post.investment(steady))
    layers += drop_lines(
        point,
        x_label=text(f"{prefix}mark.capital_shifted"),
        y_label=None,
        layer_id="macro.growth.steady.shifted.guide",
    )
    layers += marked_point(
        point,
        point_name(0, prime=1),
        layer_id="macro.growth.steady.shifted",
        role="macro.point.shifted",
    )
    return layers
