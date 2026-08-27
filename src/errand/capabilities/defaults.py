from errand.capabilities.open_app import OpenAppCapability
from errand.capabilities.registry import CapabilityRegistry


def create_default_capability_registry() -> CapabilityRegistry:

    registry = CapabilityRegistry()

    registry.register(OpenAppCapability())

    return registry