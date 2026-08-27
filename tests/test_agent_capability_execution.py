from errand.agent.agent import Agent
from errand.agent.decision import AgentDecision
from errand.capabilities.base import Capability
from errand.capabilities.registry import CapabilityRegistry
from errand.core.capability_executor import CapabilityExecutor


class FakeCapability(Capability):

    @property
    def name(self):
        return "say_hello"

    @property
    def description(self):
        return "Say hello to someone."

    @property
    def input_schema(self):
        return {
            "name": str,
        }

    def execute(self, inputs):
        return f"Hello, {inputs['name']}!"


class FakeAgentModel:

    def __init__(self):
        self.calls = 0

    def decide(self, context):

        self.calls += 1

        if self.calls == 1:
            return AgentDecision(
                type="capability",
                capability="say_hello",
                inputs={
                    "name": "Varsha",
                },
            )

        return AgentDecision(
            type="finish",
            result="Done.",
        )


def test_agent_executes_capability():

    registry = CapabilityRegistry()
    registry.register(FakeCapability())

    executor = CapabilityExecutor(registry)
    model = FakeAgentModel()

    agent = Agent(
        model=model,
        executor=executor,
    )

    result = agent.run("Say hello to Varsha")

    assert result.type == "finish"
    assert result.result == "Done."

    assert model.calls == 2