"""Shares and gaps of the AD-AS figures."""

from __future__ import annotations

SHIFT_ARROW_SHARE = 0.55
"""Height of the arrow showing a curve's shift, as a share of the vertical axis."""

AMBIGUOUS_SPAN_SHARE = 0.08
"""Length of each arrow of an ambiguous shift, as a share of the horizontal axis."""

DEMAND_FLOOR_SHARE = 0.2
"""Demand curves end at this share of the price axis, so shifted curves end side by side."""

MARKED_OUTPUTS = 2
"""How many leading points of an adjustment path get a mark for their output on the axis."""

SAME_OUTPUT = 0.01
"""Outputs within this share of natural output are not marked apart from it."""

LABEL_GAP = 4.0
"""Gap in points between an arrow and the text beside it."""
