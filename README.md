# macro-viz

`macro-viz` is the EconViz package for textbook macroeconomic analysis and diagrams. It targets
introductory and intermediate models whose equations are given and need to be analysed or drawn.

The current `0.2.0.dev0` milestone provides the Keynesian goods market (consumption function,
Keynesian cross, multiplier) as typed models and MosaicKit figures, and an optional animation
layer. Statistics-style data charts and accounting-style box diagrams are out of scope: the package
draws models whose equations are given.

## Quick start

```python
from macro_viz.keynesian import ConsumptionFunction, KeynesianCross, analyze_autonomous_shift
from macro_viz.visuals import multiplier_canvas

model = KeynesianCross(ConsumptionFunction(20, 0.6), investment=20, government=30, taxes=20)
shift = analyze_autonomous_shift(model, change=30)

multiplier_canvas(shift, title="A rise in autonomous spending").save("multiplier.svg")
```

Every visual builder accepts `title=None` (no title), returns a MosaicKit `Canvas`, and emits
stable `macro.*` layer IDs. Axes carry arrowheads, curves are named directly at their end instead
of in a legend, and values are marked on the axes with dotted guides. Built-in words come from a
locale table keyed by stable ids in English, Traditional Chinese, and Simplified Chinese, and every
text can be replaced through `labels=`. Nothing else is written into the drawing code: sizes,
widths, colours, and fonts come from the theme and the settings below.

## Keynesian goods market

`macro_viz.keynesian` holds the renderer-free model: `ConsumptionFunction(c0, c1)`,
`KeynesianCross(consumption, investment, government, taxes)` (equilibrium `Y = Z`, multiplier
`1 / (1 - c1)`), `CurvedDemand(function, lower, upper)` for a non-linear demand curve, and
`analyze_autonomous_shift(model, change)`, which returns both equilibria, the direction of the
change, and the rounds of the multiplier process. The builders `consumption_function_canvas`,
`keynesian_cross_canvas`, and `multiplier_canvas` draw them with arrowed axes, direct curve names,
dotted guides to marks on the axes, an old position that stays heavy and a new one that is thin
and dashed. Every text is a label id of the locale table and can be replaced through `labels=`;
the axes follow the model (`x_max` and `extent` change them).

## Money market

`macro_viz.money` holds `MoneyDemand(nominal_income, liquidity, rate_max)` (`Md = $Y L(i)` with a
decreasing `L`), `MoneyMarket(demand, supply)` whose `equilibrium()` solves `$Y L(i) = M` for the
interest rate, and `analyze_income_shift` / `analyze_supply_shift`, which return the baseline and
post-change markets with the direction of the rate and of the money stock. `money_market_canvas`
draws the market (and, given a shift, the old position heavy, the new one thin and dashed, A and
A', and an arrow); `money_demand_canvas` shows the demand curve before and after a change in
nominal income at one interest rate.

## Aggregate supply and demand

`macro_viz.adas` holds `AggregateSupply` (`P = scale * Pe * h(Y)` with `h(Yn) = 1`; `linear(...)`
or any increasing `h`), `AggregateDemand` (`Y = A + k * M / P`), `ASADModel` whose `equilibrium()`
returns output, price level, and the gap against natural output (recessionary, inflationary, or
none), `analyze_demand_shock` and `analyze_supply_shock` with direction metadata, and
`employment(Y, A)`. Natural output is an input; the wage-setting derivation is a separate model.
`adas_canvas` draws the crossing, the natural-output marker, and optionally a shock, a productivity
note, or the unknown direction of a demand shift; `aggregate_supply_canvas` and
`aggregate_demand_canvas` draw one curve and its shifts.

`analyze_adjustment` lists the equilibria as expectations catch up (the expected price becomes
the price just observed) after a demand or supply shock, ending at natural output;
`adas_adjustment_canvas` draws the shifting supply curves and the path A, A', A''.

## IS-LM

`macro_viz.islm.ISLM` is linear: `IS: Y = multiplier * (a - b R)`, `LM: m = d Y - h R` (a vertical
LM at `h = 0`, nearly horizontal for a large `h`). `equilibrium()` solves both; `analyze_fiscal_policy`
and `analyze_monetary_policy` return baseline and post models with directions and, for fiscal
policy, the crowding out. `islm_canvas` draws IS, LM, A, and a shift; the three-panel
decompositions and policy-mix panels belong with the linked-panel diagrams.

## Solow growth

`macro_viz.growth.Solow` takes any increasing concave production function (or
`Solow.cobb_douglas`) with the saving rate, depreciation, and population and technology growth.
It gives the steady state, golden-rule capital and saving rate, and one-period capital
accumulation; `analyze_change` compares steady states, and `simulate` returns the discrete
transition after a change (`SolowPath`: capital, output, growth rates, and log output including
the trend of technology). Figures: `production_function_canvas`, `solow_canvas` (with convergence
arrows), `golden_rule_canvas`, `solow_level_path_canvas`, `solow_log_path_canvas`,
`solow_growth_rate_canvas`; `effective=True` switches the labels to per effective worker.

## Natural rate of unemployment

`macro_viz.labor.WagePriceSetting` is wage setting `WS: W/P = ws_scale * (level + z - slope * u)`
against price setting `PS: W/P = ps_scale / (1 + m)`; `natural_rate()` solves `WS = PS`.
`compare` reports the direction of the natural rate and real wage after a change in benefits `z`,
markup `m`, or productivity (a common shift leaves `u_n` unchanged, a differential one moves it).
`wsps_canvas` draws the crossing and shifts on the unemployment axis, or on the employment axis
(`labor_force=`) with braces for `N` and `U`. Natural output from this model is an input to the
AS-AD functions.

## Linked panels (four and five quadrants)

`four_panel_canvas(scenario)` draws the labour market, AD-AS, the production function and the
45-degree line on one grid; `five_panel_canvas(scenario)` adds IS-LM above AD-AS so the right
column shares one `Y` axis. A `Scenario` is a baseline `MacroEconomy` and labelled `Step`s (`A`, `B`,
`C`), each a `Shock` of parameters (capital, money, expenditure, expected price) at a given or
market-clearing price level. Equations (documented in `macro_viz.panels.model`):

```text
W = p f(N, K)     labour demand          W = pe h(N)      labour supply
Y = K^theta (a N - b N^2 / 2)            production function, f = dY/dN
IS: Y = X - e R   LM: M / p = k Y - h R  AD: Y = (X + (e / h) M / p) / (1 + e k / h)
```

`Mode.SCHEMATIC` (default) draws straight lines through the solved points, as in textbook
figures; `Mode.DERIVED` draws the curves from the equations. See `examples/scripts/four_panel.py`
and `five_panel.py`; the scenarios live in `examples/examples.toml`.

`MoneyDemand(..., zero_bound=True)` and `ISLM(..., zero_bound=True)` add the zero lower bound: money
demand goes flat at a zero rate, the LM curve is flat up to the output where money demand reaches zero
interest, and extra money or an LM shift on the flat part leaves the equilibrium unchanged.

## Animation

A figure about a shift or an adjustment animates from the same builder. `pip install
macro-viz[animation]` adds KineticKit. `macro_viz.animation.save_gif(builder, values, path)` renders
the builder's canvas at each value through MosaicKit and streams the frames into a GIF;
`save_svg` morphs between the frames' layers, matched by their stable ids, into a native animated
SVG and sets the labels with GlyphKit in the fonts of the active settings. Fix every axis range
in the builder, as `examples/scripts/keynesian_animation.py` does. Without KineticKit the static
figures work unchanged.

## Configuration

The package declares a MosaicKit schema for the `[macro.*]` portion of the shared
`econ-viz.toml`; MosaicKit owns parsing and activation. The built-in package default is colored
on a white background. Select the black-and-white manual palette explicitly for books and
handouts:

```toml
base = "default"

[macro]
palette = "manual"
language = "zh-TW"        # built-in text: en, zh-TW, zh-CN

[macro.stroke]            # points
curve = 3.5
shifted = 1.0

[macro.marker]
point = 6.5

[macro.text]
scale = 1.5               # multiplies every text size

[macro.label.curve]       # move whole label groups: point, curve, mark, region, annotation
top = "2pt"
```

Load a file once with `Config.load("econ-viz.toml").use()`. Shared per-figure
`[figure.<stem>.label."<layer-id>"]` overrides continue to be applied by MosaicKit when a canvas
is saved.

## Examples

Tracked executable examples live in `examples/scripts`; their generated images are intentionally
ignored. Sample data and titles are in `examples/examples.toml`, the manual look (black and white,
white background, TeX Gyre Pagella, direct labels, arrowed axes) in `examples/econ-viz.toml`.
Both, the output folder, and the image format are command-line arguments. Regenerate locally with:

```bash
uv run python examples/scripts/keynesian.py --output examples/output
uv run python examples/scripts/keynesian_animation.py --output examples/output
```

The scripts look for the font files in `$MACRO_VIZ_FONT_DIR` and in a TeX Live installation, and
fall back to the default serif face when they are missing.

## Scope and architecture

Planned areas include AD-AS, money markets, IS-LM, Phillips curves, Solow
growth, open-economy macroeconomics, linked-panel transmission diagrams, phase portraits,
difference equations, cobweb diagrams, and the static New Keynesian three-equation model.

Models that must be derived and solved from optimization belong in `dsge-viz`. Standalone
introductory markets belong in `principle-viz`, and intertemporal consumer geometry belongs in
`utility-viz`.

The architectural direction is one way:

```text
domain model -> analysis -> typed result -> visual builder -> MosaicKit layers
```

Domain and analysis modules remain renderer-neutral. Visual builders use public MosaicKit scenes
and layers rather than importing Matplotlib or implementing a separate drawing layer.

`mosaickit` is the only direct graphics dependency. `kinetickit[raster]` is the optional
`macro-viz[animation]` extra, following utility-viz's dependency boundary; text support supplied
by `glyphkit` arrives through MosaicKit and KineticKit. `bezierkit` will become a direct dependency
only when a real macroeconomic curve-geometry feature needs it.

## Installation

The package has not been released. For development (add `--extra animation` for the animation
tests):

```bash
git clone https://github.com/EconViz/macro-viz.git
cd macro-viz
uv sync
```

## Development

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests
uv run pytest
uv build
```

The checks cover package code, numerical and edge-case tests, architecture boundaries, rendering
integration, and executable examples.
