from errand.capabilities.generator import (
    GeneratedCapability,
    GeneratedCapabilitySpec,
)
from errand.capabilities.pipeline import (
    CapabilityPipeline,
)
from errand.capabilities.sandbox import (
    SandboxResult,
)
from errand.capabilities.validator import (
    CapabilityValidationError,
)


class FakeGenerator:

    def __init__(self, generated):
        self.generated = generated
        self.generate_calls = []
        self.generate_code_calls = []

    def generate(self, name, description):

        self.generate_calls.append(
            {
                "name": name,
                "description": description,
            }
        )

        return self.generated.spec

    def generate_code(self, spec):

        self.generate_code_calls.append(spec)

        return self.generated


class FakeValidator:

    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def validate(self, source, spec):

        self.calls.append(
            {
                "source": source,
                "spec": spec,
            }
        )

        if self.error is not None:
            raise self.error


class FakeSandbox:

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def run(self, generated):

        self.calls.append(generated)

        if self.error is not None:
            raise self.error

        return self.result


def make_generated():

    spec = GeneratedCapabilitySpec(
        name="play_music",
        description="Play music.",
        inputs={
            "song": "string",
        },
    )

    source = """
from errand.capabilities.base import Capability


class PlayMusicCapability(Capability):

    @property
    def name(self):
        return "play_music"

    @property
    def description(self):
        return "Play music."

    @property
    def input_schema(self):
        return {
            "song": str,
        }

    def execute(self, inputs):
        return inputs["song"]
"""

    return GeneratedCapability(
        spec=spec,
        source=source,
    )


def make_passed_sandbox_result():

    return SandboxResult(
        passed=True,
        stdout='{"status": "passed"}',
        stderr="",
        exit_code=0,
    )


def test_pipeline_passes_when_all_stages_pass():

    generated = make_generated()

    generator = FakeGenerator(generated)

    validator = FakeValidator()

    sandbox = FakeSandbox(
        result=make_passed_sandbox_result()
    )

    pipeline = CapabilityPipeline(
        generator=generator,
        validator=validator,
        sandbox=sandbox,
    )

    result = pipeline.run(
        name="play_music",
        description="Play music.",
    )

    assert result.passed is True
    assert result.stage == "completed"

    assert result.spec == generated.spec
    assert result.generated == generated

    assert result.sandbox_result is not None
    assert result.sandbox_result.passed is True

    assert len(generator.generate_calls) == 1
    assert len(generator.generate_code_calls) == 1

    assert len(validator.calls) == 1
    assert len(sandbox.calls) == 1


def test_pipeline_stops_when_static_validation_fails():

    generated = make_generated()

    generator = FakeGenerator(generated)

    validator = FakeValidator(
        error=CapabilityValidationError(
            "unsafe capability"
        )
    )

    sandbox = FakeSandbox(
        result=make_passed_sandbox_result()
    )

    pipeline = CapabilityPipeline(
        generator=generator,
        validator=validator,
        sandbox=sandbox,
    )

    result = pipeline.run(
        name="play_music",
        description="Play music.",
    )

    assert result.passed is False
    assert result.stage == "static_validation"
    assert result.error == "unsafe capability"

    assert result.generated == generated

    assert len(validator.calls) == 1

    # Sandbox must never run if static validation fails.
    assert len(sandbox.calls) == 0


def test_pipeline_fails_when_sandbox_fails():

    generated = make_generated()

    generator = FakeGenerator(generated)

    validator = FakeValidator()

    sandbox = FakeSandbox(
        result=SandboxResult(
            passed=False,
            stdout="",
            stderr="CAPABILITY_EXECUTION_FAILED",
            exit_code=1,            
        )
    )

    pipeline = CapabilityPipeline(
        generator=generator,
        validator=validator,
        sandbox=sandbox,
    )

    result = pipeline.run(
        name="play_music",
        description="Play music.",
    )

    assert result.passed is False
    assert result.stage == "sandbox_execution"

    assert result.generated == generated

    assert result.sandbox_result is not None
    assert result.sandbox_result.passed is False

    assert len(sandbox.calls) == 1


def test_pipeline_stops_when_spec_generation_fails():

    class FailingGenerator:

        def generate(self, name, description):
            raise ValueError(
                "Gemini failed to generate specification."
            )

        def generate_code(self, spec):
            raise AssertionError(
                "generate_code should not be called."
            )

    validator = FakeValidator()

    sandbox = FakeSandbox(
        result=make_passed_sandbox_result()
    )

    pipeline = CapabilityPipeline(
        generator=FailingGenerator(),
        validator=validator,
        sandbox=sandbox,
    )

    result = pipeline.run(
        name="play_music",
        description="Play music.",
    )

    assert result.passed is False
    assert result.stage == "specification_generation"

    assert (
        result.error
        == "Gemini failed to generate specification."
    )

    assert len(validator.calls) == 0
    assert len(sandbox.calls) == 0


def test_pipeline_stops_when_code_generation_fails():

    generated = make_generated()

    class FailingGenerator:

        def generate(self, name, description):
            return generated.spec

        def generate_code(self, spec):
            raise ValueError(
                "Gemini failed to generate code."
            )

    validator = FakeValidator()

    sandbox = FakeSandbox(
        result=make_passed_sandbox_result()
    )

    pipeline = CapabilityPipeline(
        generator=FailingGenerator(),
        validator=validator,
        sandbox=sandbox,
    )

    result = pipeline.run(
        name="play_music",
        description="Play music.",
    )

    assert result.passed is False
    assert result.stage == "code_generation"

    assert result.spec == generated.spec
    assert result.generated is None

    assert (
        result.error
        == "Gemini failed to generate code."
    )

    assert len(validator.calls) == 0
    assert len(sandbox.calls) == 0