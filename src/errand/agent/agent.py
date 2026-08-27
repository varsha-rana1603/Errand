from typing import Protocol

from errand.agent.context import AgentContext
from errand.agent.decision import AgentDecision
from errand.core.capability_executor import CapabilityExecutor


class AgentModel(Protocol):
    """
    Interface implemented by an LLM-backed agent model.

    The real implementation will use Gemini.
    Tests can provide a fake implementation.
    """

    def decide(self, context: AgentContext) -> AgentDecision:
        ...


class Agent:
    """
    General-purpose Errand agent.

    The agent repeatedly:

        decide -> execute -> observe -> decide

    It can also pause and ask the user for information.
    """

    def __init__(
        self,
        model: AgentModel,
        executor: CapabilityExecutor,
        max_steps: int = 10,
    ):
        self.model = model
        self.executor = executor
        self.max_steps = max_steps

    def run(self, goal: str) -> AgentDecision:
        """
        Run a complete task from scratch.

        If the model asks the user for information, the decision
        is returned to the caller. The caller can then resume the
        same context.
        """

        context = AgentContext(goal=goal)

        return self._run_loop(context)

    def run_context(self, context: AgentContext) -> AgentDecision:
        """
        Continue an existing task using its current context.
        """

        return self._run_loop(context)

    def _run_loop(self, context: AgentContext) -> AgentDecision:

        for _ in range(self.max_steps):

            decision = self.model.decide(context)

            context.add_agent_decision(decision)

            # --------------------------------------------------
            # ASK USER
            # --------------------------------------------------

            if decision.type == "ask_user":
                return decision

            # --------------------------------------------------
            # CAPABILITY
            # --------------------------------------------------

            if decision.type == "capability":

                if not decision.capability:
                    return AgentDecision(
                        type="fail",
                        reason="Agent requested a capability without a name.",
                    )

                try:
                    result = self.executor.execute(
                        decision.capability,
                        decision.inputs,
                    )

                except Exception as exc:

                    context.add_observation(
                        {
                            "error": str(exc),
                        }
                    )

                    continue

                context.add_observation(result)

                # The agent must observe the result and decide
                # what to do next.
                continue

            # --------------------------------------------------
            # FINISH
            # --------------------------------------------------

            if decision.type == "finish":
                return decision

            # --------------------------------------------------
            # FAIL
            # --------------------------------------------------

            if decision.type == "fail":
                return decision

            # --------------------------------------------------
            # UNKNOWN DECISION
            # --------------------------------------------------

            return AgentDecision(
                type="fail",
                reason=f"Unknown decision type: {decision.type}",
            )

        return AgentDecision(
            type="fail",
            reason=(
                f"Agent exceeded maximum number of steps "
                f"({self.max_steps})."
            ),
        )
