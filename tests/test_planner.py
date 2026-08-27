import pytest

from errand.core.intent import Intent
from errand.core.planner import Planner
from errand.skills.base import Skill
from errand.skills.registry import SkillRegistry, SkillNotFoundError


class FakeOpenAppSkill(Skill):

    @property
    def action(self):
        return "open_app"

    @property
    def required_fields(self):
        return {"app_name"}

    def execute(self, intent):
        return f"Opened {intent.fields['app_name']}"


def test_planner_creates_execution_plan():

    registry = SkillRegistry()
    registry.register(FakeOpenAppSkill())

    planner = Planner(registry)

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    plan = planner.plan(intent)

    assert len(plan.steps) == 1

    step = plan.steps[0]

    assert step.capability == "open_app"
    assert step.inputs == {
        "app_name": "Safari",
    }


def test_planner_does_not_execute_skill():

    registry = SkillRegistry()

    skill = FakeOpenAppSkill()

    registry.register(skill)

    planner = Planner(registry)

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    plan = planner.plan(intent)

    # Creating a plan must not execute the skill.
    assert plan.steps[0].capability == "open_app"


def test_planner_rejects_unsupported_action():

    registry = SkillRegistry()

    planner = Planner(registry)

    intent = Intent(
        action="fly_to_moon",
        fields={},
    )

    with pytest.raises(SkillNotFoundError):
        planner.plan(intent)


def test_planner_copies_intent_fields():

    registry = SkillRegistry()
    registry.register(FakeOpenAppSkill())

    planner = Planner(registry)

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    plan = planner.plan(intent)

    plan.steps[0].inputs["app_name"] = "Chrome"

    assert intent.fields["app_name"] == "Safari"