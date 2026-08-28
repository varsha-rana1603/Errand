from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """
    State maintained while an agent is solving a task.
    """

    goal: str

    history: list[dict[str, Any]] = field(
        default_factory=list
    )

    # --------------------------------------------------
    # PENDING CAPABILITY GENERATION
    # --------------------------------------------------

    pending_capability_job: Any | None = None

    pending_capability_name: str | None = None

    pending_capability_description: str | None = None

    # --------------------------------------------------
    # HISTORY
    # --------------------------------------------------

    def add_user_message(
        self,
        message: str,
    ) -> None:

        self.history.append(
            {
                "role": "user",
                "content": message,
            }
        )

    def add_agent_decision(
        self,
        decision: Any,
    ) -> None:

        self.history.append(
            {
                "role": "agent",
                "decision": decision,
            }
        )

    def add_observation(
        self,
        observation: Any,
    ) -> None:

        self.history.append(
            {
                "role": "observation",
                "content": observation,
            }
        )

    def last_observation(self) -> Any | None:

        for entry in reversed(self.history):

            if entry["role"] == "observation":
                return entry["content"]

        return None

    def last_user_message(self) -> str | None:

        for entry in reversed(self.history):

            if entry["role"] == "user":
                return entry["content"]

        return None