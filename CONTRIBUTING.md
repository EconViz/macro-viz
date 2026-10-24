# Contributing to macro-viz

Thank you for helping build `macro-viz`.

## Development setup

```bash
git clone https://github.com/EconViz/macro-viz.git
cd macro-viz
uv sync
```

Run every check before opening a pull request:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests
uv run pytest
uv build
```

## Architecture

Economic models and analytical results must not import MosaicKit, Matplotlib, or another
rendering backend. Visual builders may translate typed results into public MosaicKit layers.
Keep changes within the package boundary documented in the project roadmap and add tests for
every public behavior.

Generated images, caches, build output, and local agent instructions must not be committed.

