import pytest

from errand.capabilities.generator import (
    GeneratedCapability,
    GeneratedCapabilitySpec,
)
from errand.capabilities.sandbox import (
    CapabilitySandbox,
)


def make_generated(source: str) -> GeneratedCapability:

    spec = GeneratedCapabilitySpec(
        name="test_capability",
        description="A test capability.",
        inputs={},
    )

    return GeneratedCapability(
        spec=spec,
        source=source,
    )


def valid_source():

    return """
from errand.capabilities.base import Capability


class TestCapability(Capability):

    @property
    def name(self):
        return "test_capability"

    @property
    def description(self):
        return "A test capability."

    @property
    def input_schema(self):
        return {}

    def execute(self, inputs):
        return "sandbox works"
"""


@pytest.mark.skipif(
    __import__("shutil").which("docker") is None,
    reason="Docker is not installed.",
)
def test_sandbox_executes_valid_capability():

    sandbox = CapabilitySandbox()

    result = sandbox.run(
        make_generated(valid_source())
    )

    assert result.passed
    assert "sandbox works" in result.stdout


@pytest.mark.skipif(
    __import__("shutil").which("docker") is None,
    reason="Docker is not installed.",
)
def test_sandbox_rejects_capability_with_runtime_failure():

    source = valid_source().replace(
        'return "sandbox works"',
        'raise RuntimeError("intentional failure")',
    )

    sandbox = CapabilitySandbox()

    result = sandbox.run(
        make_generated(source)
    )

    assert not result.passed
    assert result.exit_code != 0
    assert "CAPABILITY_EXECUTION_FAILED" in result.stderr


@pytest.mark.skipif(
    __import__("shutil").which("docker") is None,
    reason="Docker is not installed.",
)
def test_sandbox_supports_string_inputs():

    source = """
from errand.capabilities.base import Capability


class TestCapability(Capability):

    @property
    def name(self):
        return "test_capability"

    @property
    def description(self):
        return "A test capability."

    @property
    def input_schema(self):
        return {
            "message": str,
        }

    def execute(self, inputs):
        return inputs["message"]
"""

    sandbox = CapabilitySandbox()

    result = sandbox.run(
        make_generated(source)
    )

    assert result.passed
    assert "sandbox_test" in result.stdout