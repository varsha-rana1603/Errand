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


class FakeSecondSkill(Skill):

    @property
    def action(self):
        return "second_action"

    @property
    def required_fields(self):
        return set()

    def execute(self, intent):
        return "Second action executed"


def test_executor_executes_plan():

    registry = SkillRegistry()

    registry.register(FakeOpenAppSkill())

    executor = Executor(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="open_app",
                inputs={
                    "app_name": "Safari",
                },
            )
        ]
    )

    results = executor.execute(plan)

    assert results == [
        "Opened Safari",
    ]


def test_executor_executes_multiple_steps_in_order():

    registry = SkillRegistry()

    registry.register(FakeOpenAppSkill())
    registry.register(FakeSecondSkill())

    executor = Executor(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="open_app",
                inputs={
                    "app_name": "Safari",
                },
            ),
            PlanStep(
                capability="second_action",
                inputs={},
            ),
        ]
    )

    results = executor.execute(plan)

    assert results == [
        "Opened Safari",
        "Second action executed",
    ]


def test_executor_does_not_modify_plan_inputs():

    registry = SkillRegistry()
    registry.register(FakeOpenAppSkill())

    executor = Executor(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="open_app",
                inputs={
                    "app_name": "Safari",
                },
            )
        ]
    )

    executor.execute(plan)

    assert plan.steps[0].inputs == {
        "app_name": "Safari",
    }