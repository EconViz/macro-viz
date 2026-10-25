"""Medium-run adjustment of the AS-AD model as expectations catch up.

The expectation rule is a given equation, not a solved model: wage setters expect the price level
that was just observed, so ``Pe`` for the next period is the price level of the current
equilibrium. Each revision shifts aggregate supply, and the economy slides along aggregate demand
until output is back at natural output and the price level equals its expected value.
"""

from __future__ import annotations

from dataclasses import dataclass

from macro_viz.adas.analysis import ASADShift
from macro_viz.adas.models import ASADEquilibrium, ASADModel, Gap
from macro_viz.errors import ValidationError

DEFAULT_ROUNDS = 0
"""How many expectation revisions a path lists between the impact of a shock and the medium run."""


@dataclass(frozen=True, slots=True)
class AdjustmentStep:
    """One point of the path: the model in force and its short-run equilibrium."""

    index: int
    model: ASADModel
    equilibrium: ASADEquilibrium


@dataclass(frozen=True, slots=True)
class AdjustmentPath:
    """The successive short-run equilibria after a shock, and where they end.

    ``steps[0]`` is the starting point (before the shock, if there is one), the next step is the
    impact of the shock, and each later step follows a revision of the expected price level.
    ``medium_run`` is the equilibrium the revisions converge to: output at natural output, price
    level equal to its expected value.
    """

    steps: tuple[AdjustmentStep, ...]
    medium_run: ASADEquilibrium
    shift: ASADShift | None = None

    @property
    def outputs(self) -> tuple[float, ...]:
        return tuple(step.equilibrium.output for step in self.steps)

    @property
    def prices(self) -> tuple[float, ...]:
        return tuple(step.equilibrium.price for step in self.steps)


def _medium_run(model: ASADModel) -> ASADEquilibrium:
    """Output at natural output, with the price level aggregate demand gives there."""
    natural = model.supply.effective_natural_output
    price = model.demand.price(natural)
    return ASADEquilibrium(
        output=natural,
        price=price,
        natural_output=natural,
        expected_price=price,
        gap=Gap.NONE,
    )


def analyze_adjustment(
    subject: ASADModel | ASADShift, rounds: int = DEFAULT_ROUNDS
) -> AdjustmentPath:
    """List the equilibria as expectations catch up, for ``rounds`` revisions.

    Given an ``ASADModel`` the path starts at its (possibly off-natural) equilibrium. Given an
    ``ASADShift`` it starts at the baseline equilibrium, then shows the impact of the shock,
    then the revisions.
    """
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        raise ValidationError("rounds must be a non-negative integer")
    if isinstance(subject, ASADShift):
        shift: ASADShift | None = subject
        models = [subject.baseline, subject.post]
    else:
        shift = None
        models = [subject]
    final_model = models[-1]
    current = final_model
    for _ in range(rounds):
        current = current.with_supply(
            current.supply.with_expected_price(current.equilibrium().price)
        )
        models.append(current)
    steps = tuple(
        AdjustmentStep(index, model, model.equilibrium()) for index, model in enumerate(models)
    )
    return AdjustmentPath(steps, _medium_run(final_model), shift)
