#Defines teh structired decisions LLM is allowed to make

from dataclasses import dataclass , field
from typing import Any, Literal

DecisionType = Literal[
    "capability",
    "ask_user",
    "finish",
    "fail"
]

@dataclass(frozen = True)
class AgentDecision:
    #A single decision made by the Errand agent

    type: DecisionType
    capability: str | None = None
    inputs: dict[str, Any] = field(default_factory = dict)
    question: str | None = None
    result: str | None = None
    reason: str | None = None
    