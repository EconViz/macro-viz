"""One panel of a linked-panel figure."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from mosaickit import (
    ArrowPlacement,
    Canvas,
    Layer,
    MarkerLayer,
    PathLayer,
    TextLayer,
)

from macro_viz.config import active_config
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
from macro_viz.visuals._placement import (
    CURVE_ORDER,
    POINT_ORDER,
    Placed,
    PlacementOptions,
    Scene,
    place,
    text_box,
)
from macro_viz.visuals.panels._context import _Context, _present
from macro_viz.visuals.panels._preset import ARROW, DIAGONAL_REACH, UPPER_RIGHT_TAIL_LABELS
from macro_viz.visuals.panels._ticks import _tick_box, _upper_right_of_tail


def _panel_canvas(
    ctx: _Context,
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    arrows: Sequence[ShiftArrow],
    ticks: Sequence[Layer],
    pieces: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    title: str | None,
    steps: Collection[str],
    width: float,
    height: float,
    size_pt: tuple[float, float],
    placement: PlacementOptions,
) -> Canvas:
    x_range, y_range = ctx.x_range(panel), ctx.y_range(panel)
    spec = canvas_spec(
        x_range, y_range, width=panel.cols * width, height=panel.rows * height, title=title
    )
    canvas = new_canvas(spec)
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
    options = active_config().settings.options
    text_size = options.label_size * options.text_scale
    small_size = options.annotation_size * options.text_scale
    scale = (size_pt[0] / (x_range[1] - x_range[0]), size_pt[1] / (y_range[1] - y_range[0]))
    origin = (x_range[0], y_range[0])

    def pt(point: tuple[float, float]) -> tuple[float, float]:
        return ((point[0] - origin[0]) * scale[0], (point[1] - origin[1]) * scale[1])

    scene = Scene(limits=(0.0, 0.0, size_pt[0], size_pt[1]), dot_radius=options.point_size**0.5)
    scene.add_polyline([pt((0.0, 0.0)), pt((lx, 0.0))])
    scene.add_polyline([pt((0.0, 0.0)), pt((0.0, ly))])
    for corner, anchor_box in (
        (pt((lx, 0.0)), "x"),
        (pt((0.0, ly)), "y"),
    ):
        w, h = text_box("W", text_size, placement)
        if anchor_box == "x":
            scene.boxes.append((corner[0], corner[1] - h / 2, corner[0] + 2 * w, corner[1] + h / 2))
        else:
            scene.boxes.append((corner[0] - w, corner[1], corner[0] + w, corner[1] + 2 * h))
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
        scene.add_polyline([pt((0.0, 0.0)), pt((tip, tip))])
        w, h = text_box("45", small_size, placement)
        top = pt((tip, tip))
        scene.boxes.append((top[0], top[1], top[0] + w + 6, top[1] + h + 2))
    for piece in pieces:
        scene.add_polyline([pt(piece[0]), pt(piece[1])])
    for arrow in arrows:
        scene.add_polyline([pt(point) for point in arrow.points])
    for tick in ticks:
        scene.boxes.append(_tick_box(tick, scale, origin, small_size, placement))
    for curve in curves:
        scene.add_polyline([pt(point) for point in curve.points])
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
            scene.dots.append(pt(location))

    def put(
        layer_id: str, role: str, text: str, placed: Placed, size: float, *, at_leader: bool = True
    ) -> None:
        scene.boxes.append(placed.box)
        position = (
            placed.position[0] / scale[0] + origin[0],
            placed.position[1] / scale[1] + origin[1],
        )
        canvas.add(
            TextLayer(
                position, text, id=layer_id, role=role, anchor=placed.anchor, math=True, z_index=7
            )
        )
        if placed.leader is not None and at_leader:
            start, end = placed.leader
            canvas.add(
                PathLayer(
                    tuple(
                        (v[0] / scale[0] + origin[0], v[1] / scale[1] + origin[1])
                        for v in (start, end)
                    ),
                    id=f"{layer_id}.leader",
                    role="macro.link.leader",
                    clip=False,
                    z_index=6,
                )
            )

    counts: dict[str, int] = {}
    for curve in curves:
        number = counts.get(curve.family, 0)
        counts[curve.family] = number + 1
        base = f"macro.panels.{panel.key}.{curve.family}.{number}"
        role = "macro.curve.panel" if curve.main else "macro.curve.panel.shifted"
        canvas.add(PathLayer(curve.points, id=base, role=role, z_index=2))
    for curve in curves:
        number = [c for c in curves if c.family == curve.family].index(curve)
        base = f"macro.panels.{panel.key}.{curve.family}.{number}"
        role = "macro.curve.panel" if curve.main else "macro.curve.panel.shifted"
        fields = {name: ctx.subscripted(value) for name, value in curve.fields.items()}
        label = ctx.labels(curve.label_id, **fields)
        size = text_box(label, text_size, placement)
        if "\\frac" in label:
            size = (size[0] * 1.3, size[1] * 3.0)
        anchor = pt(curve.end)
        if curve.family in UPPER_RIGHT_TAIL_LABELS:
            placed = _upper_right_of_tail(anchor, size, scene, placement)
        else:
            placed = place(anchor, size, scene, placement, CURVE_ORDER)
        put(f"{base}.label", role, label, placed, text_size)
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
    canvas.extend(ticks)
    for label, location in dots:
        layer_id = f"macro.panels.{panel.key}.point.{label}"
        canvas.add(MarkerLayer((location,), id=layer_id, role="macro.point", z_index=6))
        size = text_box(label, text_size, placement)
        placed = place(pt(location), size, scene, placement, POINT_ORDER, ignore=(pt(location),))
        put(f"{layer_id}.label", "macro.point", f"${label}$", placed, text_size)
    return canvas
