from dataclasses import dataclass, field
from typing import Any, Literal


# Defines the structured decisions the LLM is allowed to make.
DecisionType = Literal[
    "capability",
    "generate_capability",
    "ask_user",
    "finish",
    "fail",
]


@dataclass(frozen=True)
class AgentDecision:
    #A single decision made by the Errand agent.

    type: DecisionType
    capability: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    capability_description: str | None = None
    question: str | None = None
    result: str | None = None
    reason: str | None = None
