"""Compatibility import for the reorganized macro-viz API."""

from importlib import import_module as _import_module

_target = _import_module("macro_viz.money.visuals")
globals().update({name: value for name, value in vars(_target).items() if not name.startswith("_")})


def __getattr__(name: str) -> object:
    return getattr(_target, name)
