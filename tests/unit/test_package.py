from importlib import import_module


def test_modular_monolith_layers_are_importable() -> None:
    for module in (
        "omnigridx.domain",
        "omnigridx.application",
        "omnigridx.infrastructure",
        "omnigridx.web",
    ):
        assert import_module(module)
