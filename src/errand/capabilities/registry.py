"""
What does a registry do?

It answers:

"Given a capability name, what trusted implementation should
Errand execute?"
"""

from errand.capabilities.base import Capability


class CapabilityNotFoundError(Exception):
    """Raised when a requested capability is not registered."""


# ============================================================
# INPUT SCHEMA NORMALIZATION
# ============================================================

INPUT_TYPE_ALIASES = {
    "string": "string",
    str: "string",

    "integer": "integer",
    int: "integer",

    "float": "float",
    float: "float",

    "boolean": "boolean",
    bool: "boolean",
}


def normalize_input_schema(
    input_schema: dict,
) -> dict[str, str]:
    """
    Normalize a capability input schema into Errand's
    canonical representation.

    Canonical representation:

        string
        integer
        float
        boolean

    Examples:

        {"url": "string"}
            -> {"url": "string"}

        {"url": str}
            -> {"url": "string"}

        {"count": int}
            -> {"count": "integer"}

        {"enabled": bool}
            -> {"enabled": "boolean"}
    """

    if not isinstance(input_schema, dict):
        raise ValueError(
            "Capability input_schema must be a dictionary."
        )

    normalized = {}

    for name, type_ in input_schema.items():

        if not isinstance(name, str):
            raise ValueError(
                "Capability input names must be strings."
            )

        if type_ not in INPUT_TYPE_ALIASES:
            raise ValueError(
                f"Unsupported input type {type_!r} "
                f"for input '{name}'."
            )

        normalized[name] = INPUT_TYPE_ALIASES[type_]

    return normalized


class CapabilityRegistry:
    """
    Stores and retrieves Errand capabilities.
    """

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    # ========================================================
    # REGISTER
    # ========================================================

    def register(self, capability: Capability) -> None:
        """
        Register a capability.

        The capability must expose a valid input schema.
        """

        if capability.name in self._capabilities:
            raise ValueError(
                f"A capability named '{capability.name}' "
                "is already registered."
            )

        # Validate / normalize the schema before registration.
        normalized_schema = normalize_input_schema(
            capability.input_schema
        )

        # Store the capability.
        self._capabilities[capability.name] = capability

        print(
            f"[REGISTRY] Registered capability: "
            f"{capability.name}"
        )

        print(
            f"[REGISTRY] Normalized input_schema: "
            f"{normalized_schema}"
        )

    # ========================================================
    # GET
    # ========================================================

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

    # ========================================================
    # ALL
    # ========================================================

    def all(self) -> list[Capability]:
        """
        Return all registered capabilities.
        """

        return list(
            self._capabilities.values()
        )

    # ========================================================
    # MANIFEST
    # ========================================================

    def manifest(self) -> list[dict]:
        """
        Return a serializable description of all registered
        capabilities.

        The manifest uses Errand's canonical input type strings
        so it can safely be provided to an LLM.
        """

        return [
            {
                "name": capability.name,

                "description": capability.description,

                "inputs": normalize_input_schema(
                    capability.input_schema
                ),

                "requires_confirmation":
                    capability.requires_confirmation,
            }

            for capability in self._capabilities.values()
        ]
