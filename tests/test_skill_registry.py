import pytest

from errand.core.intent import Intent
from errand.skills.base import Skill
from errand.skills.registry import (
    SkillNotFoundError,
    SkillRegistry,
)


class FakeOpenAppSkill(Skill):

    @property
    def action(self):
        return "open_app"

    @property
    def required_fields(self):
        return {"app_name"}

    def execute(self, intent):
        return f"Would open {intent.fields['app_name']}"


class FakeEmailSkill(Skill):

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
        return "Would send email"


def test_register_and_resolve_skill():

    registry = SkillRegistry()

    skill = FakeOpenAppSkill()

    registry.register(skill)

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    resolved = registry.resolve(intent)

    assert resolved is skill


def test_unknown_action_raises_error():

    registry = SkillRegistry()

    intent = Intent(
        action="something_unknown",
        fields={},
    )

    with pytest.raises(SkillNotFoundError):
        registry.resolve(intent)

def test_skill_can_be_resolved_even_with_missing_fields():

    registry = SkillRegistry()

    skill = FakeOpenAppSkill()

    registry.register(skill)

    intent = Intent(
        action="open_app",
        fields={},
    )

    resolved = registry.resolve(intent)

    assert resolved is skill

def test_skill_can_require_confirmation():

    registry = SkillRegistry()

    skill = FakeEmailSkill()

    registry.register(skill)

    assert skill.requires_confirmation is True


def test_duplicate_action_is_rejected():

    registry = SkillRegistry()

    registry.register(FakeOpenAppSkill())

    with pytest.raises(ValueError):
        registry.register(FakeOpenAppSkill())