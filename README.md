# macro-viz

`macro-viz` is the EconViz package for textbook macroeconomic analysis and diagrams. It targets
introductory and intermediate models whose equations are given and need to be analysed or drawn.

The current `0.2.0.dev0` milestone provides typed national-account and business-cycle analysis,
plus renderer-neutral MosaicKit figures for:

- GDP expenditure decomposition, `Y = C + I + G + NX`
- nominal GDP, real GDP, and the GDP deflator
- CPI and lagged inflation rates
- employment, unemployment, and unemployment rates
- linear trends, local peaks and troughs, recession shading, and percentage output gaps

## Quick start

```python
from datetime import date

from macro_viz import TimeSeries
from macro_viz.accounts import analyze_gdp_series
from macro_viz.visuals import gdp_levels_canvas

dates = (date(2022, 1, 1), date(2023, 1, 1), date(2024, 1, 1))
nominal = TimeSeries("Nominal GDP", dates, (100, 110, 121), "billions USD")
real = TimeSeries("Real GDP", dates, (100, 105, 110), "billions USD")
result = analyze_gdp_series(nominal, real, base_period=dates[0])

gdp_levels_canvas(result, title="Nominal and real GDP").save("gdp.png")
```

`TimeSeries` uses strictly increasing `date` values, preserves the unit label, and represents
missing observations only with `None`. Transformations propagate missing values rather than
interpolating them. Price indexes carry an `IndexBase`, whose period and value must match an
observed point. Nominal and real GDP use the same unit and must agree in the GDP-deflator base
period. Inflation is the percentage change over the requested observation lag. Output gaps use
`100 * (actual - trend) / trend`; turning points are strict local extrema and never bridge a
missing observation.

Every visual builder accepts `title=None` (no title), returns a MosaicKit `Canvas` (a
`CanvasGrid` for the two-panel labour-market figure), and emits stable `macro.*` economic layer
IDs. Axes carry arrowheads, value axes start at a rounded bound below the data, dates are
labelled with `date_format` (default `"%Y"`), and series are named directly at their last
observation instead of in a legend. Series of different magnitude never share an axis.
Built-in words (`Peak`, `Trough`, the names of derived series, units) come from a locale table
keyed by stable ids in English, Traditional Chinese, and Simplified Chinese; every name can also
be passed in. Nothing else is written into the drawing code: sizes, widths, colours, and fonts
come from the theme and the settings below.

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
series = 2.4

[macro.marker]
turning_point = 7

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
uv run python examples/scripts/run_all.py --output examples/output
```

The scripts look for the font files in `$MACRO_VIZ_FONT_DIR` and in a TeX Live installation, and
fall back to the default serif face when they are missing.

## Scope and architecture

Planned areas include the Keynesian cross, AD-AS, money markets, IS-LM, Phillips curves, Solow
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

`mosaickit` is the only direct graphics dependency for this milestone. Text support supplied by
`glyphkit` arrives transitively through MosaicKit. `bezierkit` will become a direct dependency only
when a real macroeconomic curve-geometry feature needs it. `kinetickit[raster]` will remain an
optional dependency until macro-viz exposes a public animation API, following utility-viz's
dependency boundary. Unused lower-level packages are deliberately not listed as direct
dependencies.

## Installation

The package has not been released. For development:

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
