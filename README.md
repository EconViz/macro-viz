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

Every visual builder accepts `title=None`, returns a MosaicKit `Canvas`, and emits stable
`macro.*` economic layer IDs. The returned canvas renders and saves through MosaicKit's public
backend API.

## Configuration

The package declares a MosaicKit schema for the `[macro.*]` portion of the shared
`econ-viz.toml`; MosaicKit owns parsing and activation. The built-in package default is colored
on a white background. Select the black-and-white manual palette explicitly for books and
handouts:

```toml
base = "default"

[macro]
palette = "manual"

[macro.stroke]
series = 2.4

[macro.marker]
turning_point = 7
```

Load a file once with `Config.load("econ-viz.toml").use()`. Shared per-figure
`[figure.<stem>.label."<layer-id>"]` overrides continue to be applied by MosaicKit when a canvas
is saved.

## Examples

Tracked executable examples live in `examples/scripts`; their generated images are intentionally
ignored. They select the manual palette explicitly and can be regenerated locally with:

```bash
uv run python examples/scripts/run_all.py
```

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
