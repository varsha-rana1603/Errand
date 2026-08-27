from errand.agent.agent import Agent
from errand.agent.decision import AgentDecision
from errand.core.executor import Executor
from errand.core.plan import ExecutionPlan, PlanStep
from errand.skills.base import Skill
from errand.skills.registry import SkillRegistry


class FakeOpenAppSkill(Skill):

    @property
    def action(self):
        return "open_app"

    @property
    def required_fields(self):
        return {"app_name"}

    def execute(self, intent):
        return f"Opened {intent.fields['app_name']}"


class FakeModel:

    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def decide(self, context):

        return next(self.decisions)


def create_executor():

    registry = SkillRegistry()

    registry.register(FakeOpenAppSkill())

    return Executor(registry)


def test_agent_executes_capability_then_finishes():

    model = FakeModel(
        [
            AgentDecision(
                type="capability",
                capability="open_app",
                inputs={
                    "app_name": "Safari",
                },
            ),
            AgentDecision(
                type="finish",
                result="Safari is open.",
            ),
        ]
    )

    agent = Agent(
        model=model,
        executor=create_executor(),
    )

    result = agent.run("Open Safari")

    assert result.type == "finish"
    assert result.result == "Safari is open."


def test_agent_can_ask_user():

    model = FakeModel(
        [
            AgentDecision(
                type="ask_user",
                question="Which application should I open?",
            ),
        ]
    )

    agent = Agent(
        model=model,
        executor=create_executor(),
    )

    result = agent.run("Open an application")

    assert result.type == "ask_user"
    assert result.question == "Which application should I open?"


def test_agent_fails_when_capability_is_missing():

    model = FakeModel(
        [
            AgentDecision(
                type="capability",
                capability=None,
            ),
        ]
    )

    agent = Agent(
        model=model,
        executor=create_executor(),
    )

    result = agent.run("Do something")

    assert result.type == "fail"


def test_agent_stops_after_max_steps():

    model = FakeModel(
        [
            AgentDecision(
                type="ask_user",
                question="Something?",
            ),
        ]
    )

    agent = Agent(
        model=model,
        executor=create_executor(),
        max_steps=1,
    )

    result = agent.run("Do something")

    assert result.type == "ask_user"

def test_agent_rejects_unknown_capability():

    model = FakeModel(
        [
            AgentDecision(
                type="capability",
                capability="control_spaceship",
                inputs={},
            ),
        ]
    )

    agent = Agent(
        model=model,
        executor=create_executor(),
    )

    result = agent.run("Control a spaceship")

    assert result.type == "fail"
    assert "control_spaceship" in result.reason