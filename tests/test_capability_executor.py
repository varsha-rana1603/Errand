import pytest

from errand.capabilities.base import Capability
from errand.capabilities.registry import CapabilityRegistry
from errand.core.capability_executor import CapabilityExecutor


class FakeCapability(Capability):

    @property
    def name(self):
        return "fake_action"

    @property
    def description(self):
        return "A fake capability for testing."

    @property
    def input_schema(self):
        return {
            "message": str,
        }

    def execute(self, inputs):
        return f"Executed: {inputs['message']}"


def create_executor():
    registry = CapabilityRegistry()
    registry.register(FakeCapability())

    return CapabilityExecutor(registry)


def test_execute_capability():

    executor = create_executor()

    result = executor.execute(
        "fake_action",
        {
            "message": "hello",
        },
    )

    assert result == "Executed: hello"


def test_missing_input_is_rejected():

    executor = create_executor()

    with pytest.raises(ValueError):

        executor.execute(
            "fake_action",
            {},
        )


def test_unknown_input_is_rejected():

    executor = create_executor()

    with pytest.raises(ValueError):

        executor.execute(
            "fake_action",
            {
                "message": "hello",
                "something_else": "bad",
            },
        )


def test_wrong_input_type_is_rejected():

    executor = create_executor()

    with pytest.raises(TypeError):

        executor.execute(
            "fake_action",
            {
                "message": 123,
            },
        )


def test_unknown_capability_is_rejected():

    executor = create_executor()

    with pytest.raises(Exception):

        executor.execute(
            "does_not_exist",
            {},
        )