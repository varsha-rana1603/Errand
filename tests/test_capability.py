import pytest

from errand.capabilities.base import Capability


class FakeOpenAppCapability(Capability):

    @property
    def name(self):
        return "open_app"

    @property
    def description(self):
        return "Open a macOS application."

    @property
    def input_schema(self):
        return {
            "app_name": str,
        }

    def execute(self, inputs):
        return f"Opened {inputs['app_name']}"


class FakeSendEmailCapability(Capability):

    @property
    def name(self):
        return "send_email"

    @property
    def description(self):
        return "Send an email."

    @property
    def requires_confirmation(self):
        return True

    def execute(self, inputs):
        return "Email sent"

def test_capability_declares_input_schema():

    capability = FakeOpenAppCapability()

    assert capability.input_schema == {
        "app_name": str,
    }

def test_capability_has_name_and_description():

    capability = FakeOpenAppCapability()

    assert capability.name == "open_app"
    assert capability.description == "Open a macOS application."


def test_capability_can_execute():

    capability = FakeOpenAppCapability()

    result = capability.execute(
        {
            "app_name": "Safari",
        }
    )

    assert result == "Opened Safari"


def test_capability_does_not_require_confirmation_by_default():

    capability = FakeOpenAppCapability()

    assert capability.requires_confirmation is False


def test_irreversible_capability_can_require_confirmation():

    capability = FakeSendEmailCapability()

    assert capability.requires_confirmation is True