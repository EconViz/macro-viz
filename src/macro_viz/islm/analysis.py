"""Comparative statics of IS-LM: fiscal and monetary policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from macro_viz.core.direction import Direction
from macro_viz.islm.models import ISLM, ISLMEquilibrium


class Policy(str, Enum):
    """Which curve moves."""

    FISCAL = "fiscal"
    MONETARY = "monetary"


@dataclass(frozen=True, slots=True)
class ISLMShift:
    """Baseline and post-policy models with the direction of output and the interest rate."""

    baseline: ISLM
    post: ISLM
    policy: Policy
    output_direction: Direction
    rate_direction: Direction

    @property
    def before(self) -> ISLMEquilibrium:
        return self.baseline.equilibrium()

    @property
    def after(self) -> ISLMEquilibrium:
        return self.post.equilibrium()

    @property
    def crowding_out(self) -> float:
        """Output lost to the higher interest rate after a fiscal change.

        The IS curve moves right by ``multiplier * Δa`` at a given rate; the economy moves less
        because the rate rises. ``crowding_out`` is the difference between that horizontal shift
        and the actual rise in output (zero for a monetary change).
        """
        if self.policy is not Policy.FISCAL:
            return 0.0
        shift = self.post.multiplier * (self.post.autonomous - self.baseline.autonomous)
        return shift - (self.after.output - self.before.output)


def _shift(baseline: ISLM, post: ISLM, policy: Policy) -> ISLMShift:
    before, after = baseline.equilibrium(), post.equilibrium()
    return ISLMShift(
        baseline,
        post,
        policy,
        Direction.of(after.output - before.output),
        Direction.of(after.rate - before.rate),
    )


def analyze_fiscal_policy(model: ISLM, autonomous: float) -> ISLMShift:
    """Change autonomous spending: IS shifts; more spending raises ``Y`` and ``R``."""
    return _shift(model, model.with_autonomous(autonomous), Policy.FISCAL)


def analyze_monetary_policy(model: ISLM, real_money: float) -> ISLMShift:
    """Change real money: LM shifts; more money raises ``Y`` and lowers ``R``."""
    return _shift(model, model.with_real_money(real_money), Policy.MONETARY)
