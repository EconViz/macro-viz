"""The course scenarios of the linked-panel diagrams, built from ``examples.toml``."""

from __future__ import annotations

from typing import Any

from macro_viz.panels import (
    Curve,
    IsLm,
    IsLmSketch,
    LinearFunction,
    MacroEconomy,
    QuadraticProduction,
    RotationDirection,
    Scenario,
    ShiftDirection,
    Shock,
    Step,
)


def economy(data: dict[str, Any], *, islm: dict[str, Any] | None = None) -> MacroEconomy:
    """The shared economy of ``[panels]``, with IS-LM from ``[panels.islm]`` when given."""
    block = None
    data = data["economy"]
    if islm is not None:
        block = IsLm(
            0.0,
            islm["money"],
            islm["interest_sensitivity"],
            islm["income_demand"],
            islm["interest_demand"],
        )
    built = MacroEconomy(
        QuadraticProduction(data["productivity"], data["curvature"], data["elasticity"]),
        LinearFunction(data["labor_intercept"], data["labor_slope"]),
        data["capital"],
        data["expected_price"],
        block,
    )
    return built.calibrated(islm["rate"]) if islm is not None else built


def money_sas(data: dict[str, Any]) -> Scenario:
    """A money-supply increase with prices that adjust along SRAS (A, then B)."""
    base = economy(data, islm=data["islm"])
    assert base.islm is not None
    factor = data["money_sas"]["money_factor"]
    return Scenario(base, (Step("A"), Step("B", Shock(money=base.islm.money * factor))))


def money_illusion(data: dict[str, Any]) -> Scenario:
    """A price rise to ``price_after``: without illusion (C, on LRAS) and with it (K, on SRAS)."""
    table = data["money_illusion"]
    base = economy(data)
    price = table["price_after"]
    return Scenario(
        base,
        (
            Step("A", price=base.expected_price),
            Step("C", Shock(expected_price=price), price=price),
            Step("K", price=price),
        ),
    )


def capital(data: dict[str, Any]) -> Scenario:
    """User-selected outward rotations raise capacity; the model solves the shared points."""
    table = data["capital"]
    base = economy(data, islm=data["islm"])
    movements = (
        base.curve(Curve.PRODUCTION).rotate(RotationDirection.OUTWARD),
        base.curve(Curve.LABOR_DEMAND).rotate(RotationDirection.OUTWARD),
        base.curve(Curve.LM).shift(ShiftDirection.RIGHT),
    )
    sketch = IsLmSketch(("A", "C"), table["rate"], table["is_slope"], table["lm_slope"])
    return Scenario(
        base,
        (
            Step("A", price=base.expected_price),
            Step("B", price=base.expected_price, movements=movements),
            Step("C", price=table["price_after"], movements=movements),
        ),
        sketch,
    )


def expenditure(data: dict[str, Any]) -> Scenario:
    """An expenditure shock: short run (B) and after expectations adjust (C), all derived."""
    base = economy(data, islm=data["islm"])
    assert base.islm is not None
    shock = Shock(expenditure=base.islm.expenditure * data["expenditure"]["expenditure_factor"])
    return Scenario(base, (Step("A"), Step("B", shock), Step("C", shock, adjust_expectations=True)))


def hidden(data: dict[str, Any], name: str) -> tuple[tuple[str, str], ...]:
    return tuple((v, label) for v, label in data[name].get("hidden_ticks", ()))


__all__ = ["capital", "economy", "expenditure", "hidden", "money_illusion", "money_sas"]
