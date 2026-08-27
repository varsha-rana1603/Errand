from unittest.mock import patch

from errand.core.intent import Intent
from errand.skills.open_app import OpenAppSkill


def test_open_app_skill_metadata():

    skill = OpenAppSkill()

    assert skill.action == "open_app"

    assert skill.required_fields == {"app_name"}

    assert skill.requires_confirmation is False


def test_open_app_skill_can_handle_valid_intent():

    skill = OpenAppSkill()

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    assert skill.can_handle(intent)


@patch("errand.skills.open_app.subprocess.run")
def test_open_app_executes_native_mac_command(mock_run):

    skill = OpenAppSkill()

    intent = Intent(
        action="open_app",
        fields={
            "app_name": "Safari",
        },
    )

    result = skill.execute(intent)

    mock_run.assert_called_once_with(
        ["open", "-a", "Safari"],
        check=True,
    )

    assert result == "Opened Safari."