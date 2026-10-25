"""Transitions and comparative statics of the Solow model."""

from __future__ import annotations

from dataclasses import dataclass

from macro_viz.direction import Direction
from macro_viz.errors import ValidationError
from macro_viz.growth.models import Solow, SolowPath


@dataclass(frozen=True, slots=True)
class SteadyStateShift:
    """Baseline and post-change steady states with the direction of each change."""

    baseline: Solow
    post: Solow
    capital_direction: Direction
    output_direction: Direction

    @property
    def before(self) -> float:
        return self.baseline.steady_state()

    @property
    def after(self) -> float:
        return self.post.steady_state()


def analyze_change(baseline: Solow, post: Solow) -> SteadyStateShift:
    """Compare two parameter sets by their steady states."""
    before, after = baseline.steady_state(), post.steady_state()
    return SteadyStateShift(
        baseline,
        post,
        Direction.of(after - before),
        Direction.of(post.output(after) - baseline.output(before)),
    )


def simulate(baseline: Solow, post: Solow, *, periods: int, change_period: int) -> SolowPath:
    """Capital and output from the baseline steady state, switching to ``post`` at a period.

    Before ``change_period`` the economy sits at the baseline steady state; from then on,
    capital follows ``k' = k + s f(k) - (delta + gN + gA) k`` with the post parameters, which
    converges monotonically to the new steady state.
    """
    if periods < 2 or not 0 <= change_period < periods:
        raise ValidationError("periods must be at least 2 and change_period inside them")
    capital = baseline.steady_state()
    path = [capital]
    for t in range(1, periods):
        capital = post.next_capital(capital) if t > change_period else capital
        path.append(capital)
    outputs = tuple(
        (post if t >= change_period else baseline).output(k) for t, k in enumerate(path)
    )
    return SolowPath(tuple(path), outputs, change_period, baseline, post)
