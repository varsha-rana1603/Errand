from unittest.mock import patch

from errand.capabilities.open_app import OpenAppCapability


def test_open_app_capability_has_correct_metadata():

    capability = OpenAppCapability()

    assert capability.name == "open_app"

    assert capability.description == "Open a macOS application."

    assert capability.input_schema == {
        "app_name": str,
    }

    assert capability.requires_confirmation is False


@patch("errand.capabilities.open_app.subprocess.run")
def test_open_app_capability_executes(mock_run):

    capability = OpenAppCapability()

    result = capability.execute(
        {
            "app_name": "Safari",
        }
    )

    mock_run.assert_called_once_with(
        ["open", "-a", "Safari"],
        check=True,
    )

    assert result == "Opened Safari."