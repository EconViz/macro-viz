"""Shared visual presets for transmission derivation diagrams."""

ID_ROOT = "macro.transmission"
"""Prefix of every layer id of a transmission derivation, followed by the figure and the part."""

GRID_COLUMN_GAP = 0.22
GRID_ROW_GAP = 0.14
"""Gaps between derivation panels as shares of one panel."""

GRID_OUTER = 0.02
"""Margin around derivation grids as a share of the figure."""

DERIVATION_WIDTH = 4.6
DERIVATION_HEIGHT = 4.2
"""Compact fixed panel dimensions for the two- and three-panel derivations."""

AD_DERIVATION_WIDTH = 5.0
"""Wider panels keep IS and LM gentle on screen in the stacked AD derivation."""

AD_DERIVATION_HEIGHT = 5.0
"""Roomier panels for the stacked AD derivation."""

AD_TAIL = 0.9
"""Extra solved-state span kept beyond A and B on the derived AD line."""

AD_ISLM_TAIL = 1.4
"""Extra span kept beyond the solved states on the IS and LM lines."""

AD_LM_TAIL = 1.0
"""Extra span kept beyond the solved states on the LM lines, so the shift arrow stays inside."""

AD_GAP_SHARE = 0.16
"""Horizontal distance between A and B as a share of the output axis."""

LM_DISPLAY_SLOPE = 0.8
"""Absolute screen slope of the IS-LM lines in the AD derivation."""

AD_DISPLAY_SLOPE = 0.9
"""Absolute screen slope of the derived AD line."""

LM_DERIVATION_HEIGHT = 3.2
"""Compact height of the wide, side-by-side LM derivation."""

DERIVED_TAIL = 0.25
"""Extra solved-state span kept beyond the outer point of a derived line."""

INVESTMENT_TO_IS_SLOPE = 1.15
"""The investment schedule is slightly steeper on screen than the derived IS curve."""

LIQUIDITY_DISPLAY_SLOPE = 0.75
"""Absolute screen slope of the parallel liquidity-demand schedules."""

LIQUIDITY_TAIL_SHARE = 0.3
"""Horizontal reach of either side of a liquidity-demand equilibrium."""

LM_TAIL_SHARE = 0.9
"""Extra solved-state span shown at either end of the derived LM segment."""

AS_GAP_SHARE = 0.16
"""Distance between A and B as a share of the N and Y axes in the AS derivation."""

AS_SUPPLY_DISPLAY_SLOPE = 0.8
"""Absolute screen slope of the labour-supply line in the AS derivation."""

AS_SRAS_DISPLAY_SLOPE = 0.9
"""Absolute screen slope of the SRAS line in the AS derivation."""

AS_TAIL = 0.9
"""Extra solved-state span kept beyond A and B on the AS derivation lines."""

AS_DEMAND_TAIL = 2.6
"""Extra solved-state span kept left of A on labour demand, so the shift arrow has room."""

AS_PAD = {"N": 0.3, "Y": 0.08}
"""Room right of the N and Y axes for curve names in the AS derivation."""

SHIFTED_NAME_SIDE = "above"
"""Side of its end where a shifted curve's name goes. The wide ``LM(M/p)`` names of the old and
the shifted line would overlap upper-right of both ends, so the shifted one sits above its end."""

TAIL_LABEL_ABOVE = (0.0, 8.0)
"""Offset in points of a fixed label above the end of a vertical line."""

TAIL_LABEL_RIGHT = (8.0, 0.0)
"""Offset in points of a fixed label right of the end of a falling schedule."""

PRODUCTION_Z_INDEX = 0
"""Stacking order of the 45-degree line: beneath every schedule and guide."""

MIN_RUN = 1e-12
"""Smallest horizontal distance between solved points that still defines a line."""
