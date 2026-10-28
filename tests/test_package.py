from __future__ import annotations

import macro_viz


def test_package_version() -> None:
    assert macro_viz.__version__ == "1.0.0b1"


def test_shared_types_are_available_at_the_package_root() -> None:
    assert macro_viz.__all__ == [
        "Config",
        "LabelPlacementWarning",
        "MacroVizError",
        "ValidationError",
        "__version__",
    ]


def test_topic_derivations_keep_their_previous_imports() -> None:
    from macro_viz.adas import ADDerivation, ASDerivation
    from macro_viz.adas.linked import Scenario
    from macro_viz.adas.visuals import ad_derivation_canvas, as_derivation_canvas
    from macro_viz.islm import ISDerivation, LMDerivation
    from macro_viz.islm.visuals import is_derivation_canvas, lm_derivation_canvas
    from macro_viz.panels import Scenario as PreviousScenario
    from macro_viz.transmission import (
        ADDerivation as PreviousADDerivation,
    )
    from macro_viz.transmission import (
        ASDerivation as PreviousASDerivation,
    )
    from macro_viz.transmission import (
        ISDerivation as PreviousISDerivation,
    )
    from macro_viz.transmission import (
        LMDerivation as PreviousLMDerivation,
    )
    from macro_viz.visuals import (
        ad_derivation_canvas as PreviousADCanvas,
    )
    from macro_viz.visuals import (
        as_derivation_canvas as PreviousASCanvas,
    )
    from macro_viz.visuals import (
        is_derivation_canvas as PreviousISCanvas,
    )
    from macro_viz.visuals import (
        lm_derivation_canvas as PreviousLMCanvas,
    )

    assert (ADDerivation, ASDerivation, ISDerivation, LMDerivation, Scenario) == (
        PreviousADDerivation,
        PreviousASDerivation,
        PreviousISDerivation,
        PreviousLMDerivation,
        PreviousScenario,
    )
    assert (
        ad_derivation_canvas,
        as_derivation_canvas,
        is_derivation_canvas,
        lm_derivation_canvas,
    ) == (
        PreviousADCanvas,
        PreviousASCanvas,
        PreviousISCanvas,
        PreviousLMCanvas,
    )
