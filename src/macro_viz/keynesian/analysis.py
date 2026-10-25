"""Comparative statics of the Keynesian cross."""

from __future__ import annotations

from macro_viz.keynesian.models import AutonomousShift, Direction, KeynesianCross


def analyze_autonomous_shift(model: KeynesianCross, change: float) -> AutonomousShift:
    """Change autonomous spending by ``change`` and report both equilibria.

    Output moves by ``change / (1 - c1)``, the multiplier times the change.
    """
    post = model.shifted(change)
    return AutonomousShift(
        baseline=model,
        post=post,
        change=change,
        direction=Direction.of(change),
        output_change=post.equilibrium().output - model.equilibrium().output,
    )
