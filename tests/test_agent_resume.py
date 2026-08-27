
from errand.agent.agent import Agent
from errand.agent.context import AgentContext
from errand.agent.decision import AgentDecision


class FakeModel:

    def __init__(self):
        self.calls = 0

    def decide(self, context):

        self.calls += 1

        if self.calls == 1:
            return AgentDecision(
                type="ask_user",
                question="Which application?",
            )

        if self.calls == 2:

            # The model receives the user's answer through
            # the shared AgentContext and converts it into
            # the capability input.
            assert any(
                entry["role"] == "user"
                and entry["content"] == "Safari"
                for entry in context.history
            )

            return AgentDecision(
                type="capability",
                capability="open_app",
                inputs={
                    "app_name": "Safari",
                },
            )

        return AgentDecision(
            type="finish",
            result="Safari opened.",
        )


class FakeExecutor:

    def __init__(self):
        self.calls = []

        # Agent checks executor.registry.get(...)
        self.registry = self

    def get(self, capability):
        return capability

    def execute(self, plan):

        step = plan.steps[0]

        self.calls.append(
            (
                step.capability,
                step.inputs,
            )
        )

        return ["Opened Safari."]


def test_agent_can_resume_after_user_input():

    model = FakeModel()
    executor = FakeExecutor()

    agent = Agent(
        model=model,
        executor=executor,
    )

    context = AgentContext(
        goal="open an app"
    )

    # First invocation pauses for user input.
    decision = agent.run_context(context)

    assert decision.type == "ask_user"

    # CLI would normally do this.
    context.add_user_message("Safari")

    # Resume the SAME context.
    decision = agent.run_context(context)

    assert decision.type == "finish"

    assert executor.calls == [
        (
            "open_app",
            {
                "app_name": "Safari",
            },
        )
    ]
