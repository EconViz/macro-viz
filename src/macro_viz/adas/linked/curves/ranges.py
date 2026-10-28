"""The axis lengths of the panels."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from macro_viz.adas.linked.model import N, P, R, W, Y
from macro_viz.adas.linked.scenario import PanelState
from macro_viz.core.errors import ValidationError


@dataclass(frozen=True, slots=True)
class Ranges:
    """The length of each variable's axis; panels that show a variable share its length."""

    lengths: Mapping[str, float]

    def __getitem__(self, variable: str) -> float:
        return self.lengths[variable]


def axis_lengths(
    states: Sequence[PanelState],
    *,
    extent: float,
    overrides: Mapping[str, float] | None = None,
    natural: bool = False,
) -> Ranges:
    """Axis lengths: ``extent`` times the largest solved value of each variable.

    ``overrides`` fixes a variable's length. ``natural`` also counts natural output.
    """
    lengths: dict[str, float] = {}
    for variable in (N, W, Y, P, R):
        values = [state.values[variable] for state in states if variable in state.values]
        if variable == Y and natural:
            values += [state.economy.natural_output for state in states]
        if values:
            lengths[variable] = extent * max(values)
    lengths.update(overrides or {})
    for variable, length in lengths.items():
        if not length > 0:
            raise ValidationError(f"the axis of {variable} must have a positive length")
    return Ranges(lengths)
