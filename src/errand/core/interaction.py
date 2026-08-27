from dataclasses import dataclass
from enum import Enum


class InteractionType(Enum):
    """Types of interaction Errand can request from the user."""

    INPUT = "input"
    CONFIRMATION = "confirmation"
    EDIT = "edit"


@dataclass
class UserInteraction:
    """
    Represents something Errand needs from the user
    before continuing a workflow.
    """

    type: InteractionType
    prompt: str
    field: str | None = None