"""One panel of a linked-panel figure."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from mosaickit import (
    ArrowPlacement,
    Canvas,
    MarkerLayer,
    PathLayer,
    TextLayer,
)
from mosaickit.layout.labels import LabelOptions

from macro_viz.panels import (
    PanelSpec,
)
from macro_viz.panels.arrows import ShiftArrow
from macro_viz.panels.curves import (
    KEY_DIGITS,
    CurveSpec,
)
from macro_viz.panels.layout import DIAGONAL
from macro_viz.visuals._kit import axes_layers, canvas_spec, new_canvas
from macro_viz.visuals._labels import (
    PANEL_CURVE_SIDES,
    POINT_SIDES,
    RISING_SIDES,
    TICK_SIDES,
    UPPER_RIGHT_TAIL_LABELS,
    LabelSpec,
    family_end,
)
from macro_viz.visuals.panels._context import _Context, _present
from macro_viz.visuals.panels._preset import ARROW, DIAGONAL_REACH


def _panel_canvas(
    ctx: _Context,
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    arrows: Sequence[ShiftArrow],
    ticks: Sequence[tuple[TextLayer, str]],
    pieces: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    title: str | None,
    steps: Collection[str],
    width: float,
    height: float,
    size_pt: tuple[float, float],
    label_options: LabelOptions,
    point_label_offset: tuple[float, float] | None,
) -> Canvas:
    x_range, y_range = ctx.x_range(panel), ctx.y_range(panel)
    spec = canvas_spec(
        x_range, y_range, width=panel.cols * width, height=panel.rows * height, title=title
    )
    canvas = new_canvas(spec, axes_size=size_pt, label_options=label_options)
    lx, ly = ctx.lengths[panel.x], ctx.lengths[panel.y]
    canvas.extend(
        axes_layers(
            (0.0, lx),
            (0.0, ly),
            x_label=f"${ctx.symbol(panel.x)}$",
            y_label=f"${ctx.symbol(panel.y)}$",
            origin_label=ctx.labels("axis.origin"),
        )
    )
    if panel.kind == DIAGONAL:
        tip = DIAGONAL_REACH * min(lx, ly)
        canvas.add(
            PathLayer(
                ((0.0, 0.0), (tip, tip)),
                id=f"macro.panels.{panel.key}.diagonal",
                role="macro.diagonal",
                stroke=ARROW,
                arrow_placement=ArrowPlacement.END,
                clip=False,
            )
        )
        canvas.add(
            TextLayer(
                (tip, tip),
                ctx.labels("panels.label.diagonal"),
                id=f"macro.panels.{panel.key}.diagonal.label",
                role="macro.annotation",
                anchor="bottom-left",
                offset=(3, 2),
            )
        )
    dots: list[tuple[str, tuple[float, float]]] = []
    if panel.points:
        seen: set[tuple[float, float]] = set()
        for state in ctx.states:
            if state.label not in steps or not _present(state, panel):
                continue
            location = (state.values[panel.x], state.values[panel.y])
            key = (round(location[0], KEY_DIGITS), round(location[1], KEY_DIGITS))
            if key in seen:
                continue
            seen.add(key)
            dots.append((state.label, location))
    counts: dict[str, int] = {}
    for curve in curves:
        number = counts.get(curve.family, 0)
        counts[curve.family] = number + 1
        base = f"macro.panels.{panel.key}.{curve.family}.{number}"
        role = "macro.curve.panel" if curve.main else "macro.curve.panel.shifted"
        canvas.add(PathLayer(curve.points, id=base, role=role, z_index=2))
        fields = {name: ctx.subscripted(value) for name, value in curve.fields.items()}
        sides = RISING_SIDES if curve.family in UPPER_RIGHT_TAIL_LABELS else PANEL_CURVE_SIDES
        name = TextLayer(
            family_end(curve.points, curve.family),
            ctx.labels(curve.label_id, **fields),
            id=f"{base}.label",
            role=role,
            math=True,
            z_index=7,
        )
        canvas.add_label(name, LabelSpec(base, sides))
    for number, arrow in enumerate(arrows):
        canvas.add(
            PathLayer(
                arrow.points,
                id=f"macro.panels.{panel.key}.shift.{number}",
                role="macro.shift",
                stroke=ARROW,
                arrow_placement=ArrowPlacement.END,
                z_index=5,
            )
        )
    for number, (start, end) in enumerate(pieces):
        canvas.add(
            PathLayer(
                (start, end),
                id=f"macro.panels.{panel.key}.link.{number}",
                role="macro.link",
                clip=False,
                z_index=1,
            )
        )
    for tick, axis in ticks:
        canvas.add_label(tick, LabelSpec(sides=TICK_SIDES[axis]))
    for label, location in dots:
        layer_id = f"macro.panels.{panel.key}.point.{label}"
        canvas.add(MarkerLayer((location,), id=layer_id, role="macro.point", z_index=6))
        text = TextLayer(
            location,
            f"${label}$",
            id=f"{layer_id}.label",
            role="macro.point",
            offset=point_label_offset or (0, 0),
            anchor="bottom" if point_label_offset is not None else "center",
            math=True,
            z_index=7,
        )
        if point_label_offset is None:
            canvas.add_label(text, LabelSpec(layer_id, POINT_SIDES))
        else:
            canvas.add(text)
    return canvas
