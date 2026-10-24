# macro-viz

`macro-viz` is the EconViz package for textbook macroeconomic analysis and diagrams.
It targets introductory and intermediate models whose equations are given and need to be
analysed or drawn.

The package is currently in its scaffold stage. It does not provide economic models or diagrams
yet.

## Scope

Planned areas include national accounts, business-cycle data, the Keynesian cross, AD-AS,
money markets, IS-LM, Phillips curves, Solow growth, open-economy macroeconomics, linked-panel
transmission diagrams, phase portraits, difference equations, cobweb diagrams, and the static
New Keynesian three-equation model.

Models that must be derived and solved from optimization belong in `dsge-viz`. Standalone
introductory markets belong in `principle-viz`, and intertemporal consumer geometry belongs in
`utility-viz`.

The architectural direction is one way:

```text
domain model -> analysis -> typed result -> visual builder -> MosaicKit layers
```

Domain and analysis modules remain renderer-neutral. Visual builders will use public MosaicKit
scenes and layers rather than importing Matplotlib or implementing a separate drawing layer.

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

Configuration and examples will be added with the first real diagram API. That keeps semantic
theme roles and examples tied to a genuine consumer instead of making unused public contracts.
Future package settings will be declared as a MosaicKit schema under `[macro.*]`; MosaicKit will
continue to own parsing of the shared `econ-viz.toml` file, themes, rendering, and per-figure label
overrides.
