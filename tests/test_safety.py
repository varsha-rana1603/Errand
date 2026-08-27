from errand.core.plan import ExecutionPlan, PlanStep
from errand.core.safety import SafetyGate
from errand.skills.base import Skill
from errand.skills.registry import SkillRegistry


class FakeSafeSkill(Skill):

    @property
    def action(self):
        return "open_app"

    @property
    def required_fields(self):
        return {"app_name"}

    @property
    def requires_confirmation(self):
        return False

    def execute(self, intent):
        return "opened"


class FakeDangerousSkill(Skill):

    @property
    def action(self):
        return "send_email"

    @property
    def required_fields(self):
        return {"recipient_email", "body"}

    @property
    def requires_confirmation(self):
        return True

    def execute(self, intent):
        return "sent"


def test_safe_plan_does_not_require_confirmation():

    registry = SkillRegistry()
    registry.register(FakeSafeSkill())

    gate = SafetyGate(registry)

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

    assert gate.requires_confirmation(plan) is False


def test_dangerous_plan_requires_confirmation():

    registry = SkillRegistry()
    registry.register(FakeDangerousSkill())

    gate = SafetyGate(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="send_email",
                inputs={
                    "recipient_email": "deepa@example.com",
                    "body": "I'll be late.",
                },
            )
        ]
    )

    assert gate.requires_confirmation(plan) is True


def test_confirmation_can_be_accepted(monkeypatch):

    registry = SkillRegistry()
    registry.register(FakeDangerousSkill())

    gate = SafetyGate(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="send_email",
                inputs={
                    "recipient_email": "deepa@example.com",
                    "body": "I'll be late.",
                },
            )
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    assert gate.confirm(plan) is True


def test_confirmation_can_be_rejected(monkeypatch):

    registry = SkillRegistry()
    registry.register(FakeDangerousSkill())

    gate = SafetyGate(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="send_email",
                inputs={
                    "recipient_email": "deepa@example.com",
                    "body": "I'll be late.",
                },
            )
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "n",
    )

    assert gate.confirm(plan) is False

def test_preview_describes_plan():

    registry = SkillRegistry()
    registry.register(FakeDangerousSkill())

    gate = SafetyGate(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="send_email",
                inputs={
                    "recipient_email": "deepa@example.com",
                    "body": "I'll be late.",
                },
            )
        ]
    )

    preview = gate.preview(plan)

    assert "send_email" in preview
    assert "deepa@example.com" in preview
    assert "I'll be late." in preview