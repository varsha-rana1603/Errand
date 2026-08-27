from errand.core.intent import Intent
from errand.core.interaction import InteractionType
from errand.core.orchestrator import Orchestrator
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


class FakeEmailSkill(Skill):

    @property
    def action(self):
        return "send_email"

    @property
    def required_fields(self):
        return {"recipient_email", "body"}
    
    @property
    def field_questions(self):
        return {
            "recipient_email": "What's the recipient's email address?",
            "body": "What would you like the email to say?",
        }

    @property
    def requires_confirmation(self):
        return True

    def execute(self, intent):
        return "Email sent"


def test_ready_intent():

    registry = SkillRegistry()
    registry.register(FakeOpenAppSkill())

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    result = orchestrator.prepare(intent)

    assert result.status == "ready"
    assert result.skill is not None
    assert result.skill.action == "open_app"


def test_missing_required_field():

    registry = SkillRegistry()
    registry.register(FakeEmailSkill())

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="send_email",
        fields={
            "body": "I'll be late",
        },
    )

    result = orchestrator.prepare(intent)

    assert result.status == "needs_input"

    assert result.missing_fields == {
        "recipient_email",
    }

def test_missing_field_provides_clarification():

    registry = SkillRegistry()
    registry.register(FakeEmailSkill())

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="send_email",
        fields={
            "body": "I'll be late",
        },
    )

    result = orchestrator.prepare(intent)

    assert result.status == "needs_input"

    assert result.clarification is not None

    assert result.clarification.field == "recipient_email"

    assert (
        result.clarification.question
        == "What's the recipient's email address?"
    )

def test_missing_field_has_fallback_question():

    registry = SkillRegistry()
    registry.register(FakeOpenAppSkill())

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="open_app",
        fields={},
    )

    result = orchestrator.prepare(intent)

    assert result.status == "needs_input"

    assert result.clarification is not None

    assert result.clarification.field == "app_name"

    assert (
        result.clarification.question
        == "Please provide 'app_name'."
    )

def test_missing_field_creates_user_interaction():

    registry = SkillRegistry()
    registry.register(FakeEmailSkill())

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="send_email",
        fields={
            "body": "I'll be late",
        },
    )

    result = orchestrator.prepare(intent)

    assert result.interaction is not None

    assert result.interaction.type == InteractionType.INPUT

    assert result.interaction.field == "recipient_email"

    assert (
        result.interaction.prompt
        == "What's the recipient's email address?"
    )

def test_multiple_missing_fields():

    registry = SkillRegistry()
    registry.register(FakeEmailSkill())

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="send_email",
        fields={},
    )

    result = orchestrator.prepare(intent)

    assert result.status == "needs_input"

    assert result.missing_fields == {
        "recipient_email",
        "body",
    }


def test_unsupported_action():

    registry = SkillRegistry()

    orchestrator = Orchestrator(registry)

    intent = Intent(
        action="fly_to_moon",
        fields={},
    )

    result = orchestrator.prepare(intent)

    assert result.status == "unsupported"


def test_non_confirmed_skill_can_proceed():

    registry = SkillRegistry()
    skill = FakeOpenAppSkill()
    registry.register(skill)

    orchestrator = Orchestrator(registry)

    assert orchestrator.confirm(skill) is True


def test_confirmation_can_be_rejected(monkeypatch):

    registry = SkillRegistry()
    skill = FakeEmailSkill()
    registry.register(skill)

    orchestrator = Orchestrator(registry)

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "n",
    )

    assert orchestrator.confirm(skill) is False