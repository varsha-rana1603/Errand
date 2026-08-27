from errand.skills.defaults import create_default_registry


def test_default_registry_contains_open_app_skill():

    registry = create_default_registry()

    skill = registry.get("open_app")

    assert skill.action == "open_app"