# Changelog

All notable changes to `macro-viz` will be documented in this file.

## Unreleased

### Fixed

- Curve names, point labels and tick labels are placed by MosaicKit's global label placer
  (`mosaickit>=1.0.0rc15`) instead of the per-package sliding heuristics, so every name sits next
  to its own curve end, inside the canvas, without touching a line, marker, arrow or another
  label; with three parallel shifted LM lines each name now stays at its own line (closes #57).
  Placement runs once per figure, at one font size. A label the placer cannot place cleanly emits
  a `macro_viz.LabelPlacementWarning` (kept on `MacroCanvas.label_warnings`). New
  `visuals/_labels.py` is the single adapter.

### Removed

- `visuals/_placement.py`, `MacroCanvas.rising_names_above`, `TICK_CLEARANCE`, the private
  `_upper_right_of_tail` / `_leans` helpers and the `CURVE_NAME_WIDTH` estimate. The `placement=`
  option of `linked_panels_canvas` / `five_panel_canvas` / `four_panel_canvas` is now
  `label_options=` (a `mosaickit.layout.labels.LabelOptions`). `UPPER_RIGHT_TAIL_LABELS` is still
  exported from `macro_viz.visuals.panels`.

### Performance

- Linked-panel scenarios solve faster with identical results: the expectation search memoises its
  clearing-price evaluations and the labour-market bisection computes the capital term once
  (`QuadraticProduction.marginal_product_at`). `MacroCanvas` places curve names when the figure is
  read instead of after every `add`/`extend`. `tests/test_performance_guards.py` counts these
  evaluations; `benchmarks/bench_examples.py` times the examples by hand and is not run by CI (#58).

### Changed

- The example scripts write to `examples/output/<topic>/` instead of one flat folder, and the
  scripts themselves now sit in the same topic folders, `examples/scripts/<topic>/<script>.py`
  (run them from the repository root, e.g. `python examples/scripts/islm/islm.py`). The output
  folder is the script's parent folder, so there is no topic table to keep in sync. Topics:
  `adas` (adas, adas_adjustment), `animation` (all `*_animation` scripts and `panels_animation`),
  `growth`, `islm` (islm, islm_expectations), `keynesian`, `money` (money, central_bank_money,
  liquidity_trap), `open_economy` (open_economy, open_asad, mundell_fleming), `panels`
  (five_panel, four_panel, transmission) and `wsps`. Nine scripts that had a folder of their own
  (`adas_adjustment`, `central_bank_money`, `islm_expectations`, `liquidity_trap`,
  `mundell_fleming`, `open_asad`, `five_panel`, `four_panel`, `transmission`) now write to their
  topic's folder. `--output` still overrides the folder as
  given; file names are unchanged and generated files stay untracked. The shared ISLM and Solow
  builders moved to `examples/scripts/model_common.py`.

- `visuals.keynesian` is now a package of small modules (presets, shared base layers, consumption
  function, cross, multiplier, open-economy goods market) with the same import paths. Code is moved,
  not rewritten: every figure is identical in SVG and PNG.

- The five source files over 450 lines are now packages of small modules, split by responsibility,
  with the same import paths: `visuals.panels` (presets, geometry, context, ticks, panel, builders),
  `animation` (presets, GIF frames, geometry, typography, depicter, SVG), `panels.curves` (types,
  geometry, ranges, one builder per panel kind), `visuals.adas` and `visuals.growth`. Code is moved,
  not rewritten: every figure is identical in SVG and PNG. The line-limit test has no exemptions.

- Requires `mosaickit>=1.0.0rc14`. The AD, LM and IS derivations are declared with
  `mosaickit.diagram.Diagram` (`line`, `curve`, `point`, `drop`, `arrow`, `tail_label`, `stack`,
  `link_points`) through one wiring module, `visuals/_diagram.py` (locale labels, `macro.*` roles,
  `[macro.label.*]` nudges). Layer ids, SVG structure and PNG pixels are unchanged except the
  shifted LM name in the AD derivation, which now sits upper-right of the end of its line, clear of
  the line and of the `LM(M/p0)` name, because mosaickit sizes fractions realistically. `tailed_line` and the local `indexed` are removed.
  Tests fail on bare numbers in `visuals/transmission` and on source files over 450 lines.

- Requires `mosaickit>=1.0.0rc12`. Linked-panel and derivation grids use `CanvasGrid(...,
  spacing=GridSpacing(...))`; the private `PanelGrid` and its renderer subclass are removed. Rendered
  figures are pixel-identical.

- Requires `mosaickit>=1.0.0rc11`. The AD and AS derivation windows, tailed lines and the liquidity
  schedule use mosaickit's `centered_view`, `extend_line_through`, `clip_polyline` and
  `data_slope_for_display`; `trim` clips with `clip_polyline`. Rendered figures are unchanged.

- Figures follow the manual panel style: dashed guides, only the price `p` lowercase (other variables
  uppercase italic, interest rate `R`), a thin 45-degree line with an arrowhead and `45°` at its tip,
  curved rotation arrows, animated GIF frames padded to one size, and a
  test that no example label overlaps a line or another label.

- Single-panel figures: a moved curve is thin and solid, not dashed. A parallel shift is a straight
  arrow from the old equilibrium to the new curve (horizontal or vertical); movement arrows are solid
  and thinner than the curves. `rotation_arrow` is the only curved arrow (gentle, concave side down,
  for a change of slope). Curve names sit at the line end: lower-right, else upper-left, lower-left,
  upper-right, clear of every line.
- Linked-panel scenarios accept curve-owned movements such as
  `economy.curve(Curve.LM).shift(RIGHT)`. The caller chooses the curve and direction; macro-viz
  applies a schematic preset and solves the shared equilibrium without inferring a policy or
  real-world event. MosaicKit and BezierKit place and construct rotation markers.

### Added

- `macro_viz.transmission` and four fixed linked figures derive IS from goods markets, LM from
  money markets, AD from IS-LM, and AS from the labour market and production function. Standalone
  IS-LM and AD-AS remain available through `islm_canvas` and `adas_canvas`.
- `save_gif` animates builders that return a grid of panels; `examples/scripts/animation/panels_animation.py`
  reveals the steps A, B, C of the capital and money-illusion scenarios one after another.
- Initial installable package scaffold and development checks.
- A registered `[macro.*]` MosaicKit configuration schema: `palette`, `language`, `color.*`,
  `stroke.curve`, `stroke.shifted`, `stroke.arrow`, `stroke.guide`, `marker.point`, `text.scale`,
  and `label.<group>.<side>` label nudges for the groups `point`, `curve`, `mark`, `region`, and
  `annotation`. Colored defaults and a black-and-white manual palette.
- A locale table (`en`, `zh-TW`, `zh-CN`) of built-in figure text keyed by stable ids; every figure
  accepts `labels=` to replace any of it.
- `macro_viz.keynesian`: consumption function, Keynesian cross (linear and curved demand), and
  autonomous-spending shifts with the multiplier process, with the figures
  `consumption_function_canvas`, `keynesian_cross_canvas`, and `multiplier_canvas`.
- `macro_viz.money`: money demand and supply, the equilibrium interest rate, and comparative statics
  for nominal income and the money supply, with `money_market_canvas` and `money_demand_canvas`.
- `macro_viz.adas`: aggregate supply and demand, short-run equilibrium with gap classification, demand
  and supply shocks, and the figures `adas_canvas`, `aggregate_supply_canvas`, and
  `aggregate_demand_canvas`.
- `analyze_adjustment` and `adas_adjustment_canvas`: medium-run AS-AD adjustment paths (expectations,
  money expansion, deficit reduction, oil shock).
- `macro_viz.islm`: linear IS-LM, fiscal and monetary policy with crowding out, and `islm_canvas`.
- `macro_viz.growth`: Solow model (steady state, golden rule, transition paths) and its figures.
- `macro_viz.labor`: wage-setting and price-setting natural rate with shifts, and `wsps_canvas`.
- Zero lower bound for the money market and IS-LM (liquidity trap) with flat money demand and LM.
- `MoneyMultiplier` and `central_bank_money_canvas`: the market for central-bank money.
- `ISLMExpectations` and `islm_expectations_canvas`: IS-LM with expected inflation as a given input.
- `macro_viz.open_economy` and `open_goods_canvas`: the open-economy goods market and trade balance.
- `InterestParity`, `OpenISLM`, `interest_parity_canvas`, and `open_islm_canvas`: Mundell-Fleming building blocks.
- `analyze_devaluation`: open-economy AS-AD devaluation shift.
- A theory-diagram kit (arrowed axes, direct curve labels, dotted guides, solid moved positions) in
  the manual style.
- `macro_viz.animation` and the `macro-viz[animation]` extra: GIF and native animated SVG from any
  figure builder through KineticKit. Static figures work without it.
- `macro_viz.panels` and `four_panel_canvas` / `five_panel_canvas`: linked quadrant diagrams (labour
  market, production function, 45-degree line, AD-AS, and IS-LM above AD-AS) on one MosaicKit grid.
  Typed blocks solve the equilibria (`MacroEconomy`, `Shock`, `Scenario`) so a value shared between
  panels is one number; panels that show a variable share its axis range and dashed projections
  are drawn from data. Added the `stroke.link` and `stroke.diagonal` settings. Row, column and
  outer gaps are parameters, the 45-degree line is exactly 45 degrees, and labels are placed
  beside their anchor in the emptiest direction, with a thin leader when nothing is free.
- Executable examples that read their data, titles, output folder, and settings from files and
  arguments.

### Removed

- The data-series and national-accounts figures (GDP levels, deflator, CPI, inflation, employment
  and unemployment, unemployment rate, output gap, business cycle, GDP components), with
  `macro_viz.accounts`, `macro_viz.cycles`, `TimeSeries`, and their settings. They were never
  released; statistics-style charts are out of scope for macro-viz. The code stays in git history
  (PRs #19 and #20).
