#A capability is a small, controlled operation Errand will know how to perform 
#for e.g open_app -> Open an installed macOS application

from abc import ABC, abstractmethod


class Capability(ABC):
    """
    Base class for all Errand capabilities.

    A capability represents one controlled operation that
    Errand is allowed to perform on the user's computer.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique name used by the planner to reference this capability.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human/LLM-readable description of what this capability does.
        """
        raise NotImplementedError

    @property
    def requires_confirmation(self) -> bool:
        """
        Whether this capability requires explicit user confirmation
        before execution.
        """
        return False

    @abstractmethod
    def execute(self, inputs: dict) -> object:
        """
        Execute the capability using validated inputs.
        """
        raise NotImplementedError

    @property
    def input_schema(self) -> dict[str, type]:
        """
        Describe the inputs required by this capability.

        Keys are input names and values are their expected Python types.
        """
        return {}