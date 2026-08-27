from errand.capabilities.defaults import create_default_capability_registry


def test_default_capability_registry_contains_open_app():

    registry = create_default_capability_registry()

    capability = registry.get("open_app")

    assert capability.name == "open_app"