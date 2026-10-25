# Changelog

All notable changes to `macro-viz` will be documented in this file.

## Unreleased

### Changed

- Example figures redrawn in the manual style: arrowed axes, rounded value marks, year-only date
  marks, direct series names, no tick numbers on the waterfall, and a separate axis for each
  labour-market level (`labor_market_canvas` now returns a `CanvasGrid`).
- Built-in text, derived series names, and units come from a locale table (en, zh-TW, zh-CN) keyed
  by stable ids; analysis functions accept explicit names.
- Examples read their data, titles, output folder, and settings from files and arguments.

### Added

- `macro_viz.keynesian`: consumption function, Keynesian cross (linear and curved demand), autonomous
  spending shifts with the multiplier process, and the matching figures
  (`consumption_function_canvas`, `keynesian_cross_canvas`, `multiplier_canvas`).
- `macro_viz.animation` and the `macro-viz[animation]` extra: GIF and native animated SVG from any
  figure builder through KineticKit; theory-diagram kit (`visuals/_theory.py`) with curves, guides,
  marks, and direct labels.

- Initial installable package scaffold and development checks.
- Typed dated-series primitives with explicit units, index bases, dates, and `None` missing values.
- GDP expenditure, GDP deflator, inflation, labor-market, trend, turning-point, recession, and
  output-gap analyses.
- MosaicKit visual builders with stable `macro.*` IDs and optional titles.
- A registered `[macro.*]` MosaicKit configuration schema with colored defaults and a manual
  black-and-white palette.
- Executable local examples for every national-account and business-cycle feature.
- `language`, `stroke.curve`, `stroke.shifted`, `stroke.arrow`, `marker.point`, `text.scale`, and
  `label.<group>.<side>` settings under `[macro.*]`; label groups `point`, `curve`, `mark`,
  `region`, `annotation`.
