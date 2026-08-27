"""
What does a registry do?

it answers "Given a capability name, what trusted implementation should Errand execute?"
"""

from errand.capabilities.base import Capability

class CapabilityNotFoundError(Exception):
    """Rasied when a requested capability is not registered"""

class CapabilityRegistry:
    #Sores and retrieves Errand capabilities
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """
        Register a capability.
        """

        if capability.name in self._capabilities:
            raise ValueError(
                f"A capability named '{capability.name}' "
                "is already registered."
            )

        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability:
        """
        Retrieve a capability by name.
        """

        try:
            return self._capabilities[name]
        except KeyError:
            raise CapabilityNotFoundError(
                f"No capability registered with name '{name}'."
            )

    def all(self) -> list[Capability]:
        """
        Return all registered capabilities.
        """

        return list(self._capabilities.values())

    def manifest(self) -> list[dict]:
        """
        Return a serializable description of all registered capabilities.

        This manifest is intended to be provided to an LLM so that it
        knows what operations Errand can actually perform.
        """

        return [
            {
                "name": capability.name,
                "description": capability.description,
                "inputs": {
                    name: type_.__name__
                    for name, type_ in capability.input_schema.items()
                },
                "requires_confirmation": capability.requires_confirmation,
            }
            for capability in self._capabilities.values()
        ]