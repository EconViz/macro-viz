"""Interest parity and open-economy IS-LM figures."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas

from macro_viz.core.i18n import Labels
from macro_viz.islm.analysis import ISLMShift, analyze_fiscal_policy, analyze_monetary_policy
from macro_viz.islm.visuals import islm_canvas
from macro_viz.open_economy.models import InterestParity, OpenISLM
from macro_viz.open_economy.visuals.open_goods import open_goods_canvas as open_goods_canvas
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    HEADROOM,
    THEORY_SIZE,
    curve,
    drop_lines,
    marked_point,
    point_name,
    theory_canvas,
    trim,
)

PARITY_EXTENT = 2.0
"""Default length of the exchange-rate axis as a multiple of the expected exchange rate."""

PARITY_RATE_EXTENT = 2.0
"""Default length of the interest-rate axis as a multiple of the foreign rate."""


def interest_parity_canvas(
    parity: InterestParity,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    e_max: float | None = None,
    rate_max: float | None = None,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw the interest-parity relation with the exchange rate on the horizontal axis.

    The line passes through A, where the domestic rate equals the foreign rate ``i*`` and the
    exchange rate equals its expected value ``E^e``; both are marked on the axes.
    """
    text = Labels(labels)
    right = e_max if e_max is not None else PARITY_EXTENT * parity.expected_rate
    top = (
        rate_max if rate_max is not None else PARITY_RATE_EXTENT * parity.foreign_rate
    ) / HEADROOM
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="parity.axis.exchange",
        y_label_id="parity.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    step = right / (samples - 1)
    points = [(k * step, parity.rate(k * step)) for k in range(samples)]
    canvas.extend(
        curve(
            trim(points, right, top),
            layer_id="macro.parity.line",
            role="macro.curve.primary",
            label=text("parity.curve.parity"),
        )
    )
    anchor = (parity.expected_rate, parity.foreign_rate)
    canvas.extend(
        drop_lines(
            anchor,
            x_label=text("parity.mark.expected"),
            y_label=text("parity.mark.foreign_rate"),
            layer_id="macro.parity.anchor.guide",
        )
    )
    canvas.extend(marked_point(anchor, point_name(0), layer_id="macro.parity.anchor"))
    return canvas


def open_islm_canvas(
    model: OpenISLM,
    *,
    fiscal: float | None = None,
    money: float | None = None,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    **options: object,
) -> Canvas:
    """Draw floating-rate IS-LM (exchange rate substituted through parity).

    ``fiscal`` (new autonomous spending) or ``money`` (new real money) shifts a curve; the
    exchange rate that goes with each crossing is read from interest parity, not drawn here.
    """
    floating = model.floating_model()
    subject: object = floating
    if fiscal is not None:
        subject = analyze_fiscal_policy(floating, fiscal)
    elif money is not None:
        subject = analyze_monetary_policy(floating, money)
    assert isinstance(subject, ISLMShift) or subject is floating
    return islm_canvas(subject, title=title, labels=labels, **options)  # type: ignore[arg-type]
