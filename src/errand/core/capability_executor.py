from errand.capabilities.registry import CapabilityRegistry


class CapabilityExecutor:
    """
    Executes trusted capabilities from the CapabilityRegistry.

    The LLM never receives direct access to capability objects.
    It can only request a capability by name.
    """

    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def execute(self, capability_name: str, inputs: dict) -> object:
        capability = self.registry.get(capability_name)

        self._validate_inputs(capability, inputs)

        return capability.execute(inputs)

    def _validate_inputs(self, capability, inputs: dict) -> None:
        schema = capability.input_schema

        missing = [
            name
            for name in schema
            if name not in inputs or inputs[name] is None
        ]

        if missing:
            raise ValueError(
                f"Missing required inputs for "
                f"'{capability.name}': {missing}"
            )

        unknown = [
            name
            for name in inputs
            if name not in schema
        ]

        if unknown:
            raise ValueError(
                f"Unknown inputs for "
                f"'{capability.name}': {unknown}"
            )

        for name, expected_type in schema.items():

            value = inputs[name]

            if not isinstance(value, expected_type):
                raise TypeError(
                    f"Input '{name}' for '{capability.name}' "
                    f"must be {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )