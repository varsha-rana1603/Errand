import pytest

from errand.capabilities.base import Capability
from errand.capabilities.registry import (
    CapabilityNotFoundError,
    CapabilityRegistry,
)


class FakeOpenAppCapability(Capability):

    @property
    def name(self):
        return "open_app"

    @property
    def description(self):
        return "Open a macOS application."
    
    @property
    def input_schema(self):
        return {
            "app_name": str,
        }

    def execute(self, inputs):
        return f"Opened {inputs['app_name']}"


class FakeSearchFilesCapability(Capability):

    @property
    def name(self):
        return "search_files"

    @property
    def description(self):
        return "Search files on the computer."

    def execute(self, inputs):
        return f"Searching for {inputs['query']}"

def test_manifest_describes_registered_capabilities():

    registry = CapabilityRegistry()

    registry.register(FakeOpenAppCapability())

    manifest = registry.manifest()

    assert manifest == [
        {
            "name": "open_app",
            "description": "Open a macOS application.",
            "inputs": {
                "app_name": "str",
            },
            "requires_confirmation": False,
        }
    ]

def test_register_and_get_capability():

    registry = CapabilityRegistry()

    capability = FakeOpenAppCapability()

    registry.register(capability)

    result = registry.get("open_app")

    assert result is capability


def test_unknown_capability_raises_error():

    registry = CapabilityRegistry()

    with pytest.raises(CapabilityNotFoundError):
        registry.get("something_that_does_not_exist")


def test_duplicate_capability_is_rejected():

    registry = CapabilityRegistry()

    registry.register(FakeOpenAppCapability())

    with pytest.raises(ValueError):
        registry.register(FakeOpenAppCapability())


def test_registry_returns_all_capabilities():

    registry = CapabilityRegistry()

    open_app = FakeOpenAppCapability()
    search_files = FakeSearchFilesCapability()

    registry.register(open_app)
    registry.register(search_files)

    capabilities = registry.all()

    assert open_app in capabilities
    assert search_files in capabilities
    assert len(capabilities) == 2