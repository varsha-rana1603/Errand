import pytest

from errand.capabilities.generator import GeneratedCapabilitySpec
from errand.capabilities.validator import (
    CapabilityValidationError,
    CapabilityValidator,
)


def make_spec():
    return GeneratedCapabilitySpec(
        name="play_music",
        description="Play music.",
        inputs={
            "song": "string",
        },
    )


def valid_source():
    return """
from errand.capabilities.base import Capability


class PlayMusicCapability(Capability):

    @property
    def name(self) -> str:
        return "play_music"

    @property
    def description(self) -> str:
        return "Play music."

    @property
    def input_schema(self) -> dict[str, type]:
        return {
            "song": str,
        }

    def execute(self, inputs: dict) -> object:
        return "Playing music."
"""


def test_valid_capability_passes():

    validator = CapabilityValidator()

    validator.validate(
        valid_source(),
        make_spec(),
    )

def test_typing_import_is_allowed():

    source = """
from typing import Any

from errand.capabilities.base import Capability


class PlayMusicCapability(Capability):

    @property
    def name(self) -> str:
        return "play_music"

    @property
    def description(self) -> str:
        return "Play music."

    @property
    def input_schema(self) -> dict[str, type]:
        return {
            "song": str,
        }

    def execute(self, inputs: dict[str, Any]) -> object:
        return "Playing music."
"""

    validator = CapabilityValidator()

    validator.validate(
        source,
        make_spec(),
    )

def test_invalid_python_is_rejected():

    validator = CapabilityValidator()

    with pytest.raises(CapabilityValidationError):
        validator.validate(
            "this is not valid Python !!!",
            make_spec(),
        )


def test_eval_is_rejected():

    source = valid_source().replace(
        'return "Playing music."',
        'return eval(inputs["song"])',
    )

    validator = CapabilityValidator()

    with pytest.raises(CapabilityValidationError):
        validator.validate(source, make_spec())


def test_exec_is_rejected():

    source = valid_source().replace(
        'return "Playing music."',
        'exec(inputs["song"])',
    )

    validator = CapabilityValidator()

    with pytest.raises(CapabilityValidationError):
        validator.validate(source, make_spec())


def test_dangerous_import_is_rejected():

    source = valid_source().replace(
        "from errand.capabilities.base import Capability",
        "import socket\n"
        "from errand.capabilities.base import Capability",
    )

    validator = CapabilityValidator()

    with pytest.raises(CapabilityValidationError):
        validator.validate(source, make_spec())


def test_wrong_capability_name_is_rejected():

    source = valid_source().replace(
        'return "play_music"',
        'return "delete_everything"',
    )

    validator = CapabilityValidator()

    with pytest.raises(CapabilityValidationError):
        validator.validate(source, make_spec())


def test_multiple_capability_classes_are_rejected():

    source = valid_source() + """

class AnotherCapability(Capability):

    @property
    def name(self):
        return "another"

    @property
    def description(self):
        return "Another capability."

    def execute(self, inputs):
        return "done"
"""

    validator = CapabilityValidator()

    with pytest.raises(CapabilityValidationError):
        validator.validate(source, make_spec())