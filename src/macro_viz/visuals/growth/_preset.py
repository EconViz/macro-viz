"""Shares and limits of the growth figures."""

from __future__ import annotations

CONVERGENCE_HEIGHT_SHARE = 0.03
"""Height of the convergence arrows above the capital axis, as a share of the output axis."""

CONVERGENCE_SPAN_SHARE = 0.12
"""Length of each convergence arrow, as a share of the capital axis."""

SOLOW_EXTENT = 2.4
"""Default length of the capital axis in the Solow diagram, as a multiple of the steady state,
so saving and required investment end well apart and the steady state sits left of centre."""

PATH_HEADROOM = 0.3
"""Room above the highest value of a time path, as a share of its range."""

GOLDEN_SAMPLES_FLOOR = 0.02
"""The saving-rate axis of the golden-rule figure starts this far from zero and stops this far from
one: consumption is undefined at the ends."""
