from dataclasses import dataclass
from typing import Callable

from errand.capabilities.generator import (
    CapabilityGenerator,
    GeneratedCapability,
    GeneratedCapabilitySpec,
)
from errand.capabilities.sandbox import (
    CapabilitySandbox,
    SandboxExecutionError,
    SandboxResult,
)
from errand.capabilities.validator import (
    CapabilityValidationError,
    CapabilityValidator,
)


@dataclass(frozen=True)
class CapabilityPipelineResult:
    """
    Result of the complete capability generation pipeline.

    A successful result means:

        Gemini generated the capability
        AND
        static validation passed
        AND
        sandbox execution passed

    It does NOT mean that the capability is trusted,
    registered, or approved for permanent use.
    """

    passed: bool

    spec: GeneratedCapabilitySpec | None = None
    generated: GeneratedCapability | None = None
    sandbox_result: SandboxResult | None = None
    error: str | None = None
    stage: str | None = None


class CapabilityPipeline:
    """
    Coordinates capability generation, static validation,
    and sandbox testing.

    This class does NOT:
    - register capabilities
    - persist capabilities
    - execute capabilities on the host
    - grant trust to generated code
    """

    def __init__(
        self,
        generator: CapabilityGenerator | None = None,
        validator: CapabilityValidator | None = None,
        sandbox: CapabilitySandbox | None = None,
    ):
        self.generator = (
            generator
            if generator is not None
            else CapabilityGenerator()
        )

        self.validator = (
            validator
            if validator is not None
            else CapabilityValidator()
        )

        self.sandbox = (
            sandbox
            if sandbox is not None
            else CapabilitySandbox()
        )

    def run(
        self,
        name: str,
        description: str,
        stage_callback: Callable[[str], None] | None = None,
    ) -> CapabilityPipelineResult:
        """
        Run the complete capability-generation pipeline.

        Stages:

            1. Specification generation
            2. Code generation
            3. Static validation
            4. Sandbox execution

        Nothing is registered or persisted.
        """

        def set_stage(stage: str) -> None:
            if stage_callback is not None:
                stage_callback(stage)

        # ------------------------------------------------------
        # SPECIFICATION GENERATION
        # ------------------------------------------------------

        set_stage("specification_generation")

        try:
            spec = self.generator.generate(
                name=name,
                description=description,
            )

        except Exception as exc:
            return CapabilityPipelineResult(
                passed=False,
                error=str(exc),
                stage="specification_generation",
            )

        # ------------------------------------------------------
        # CODE GENERATION
        # ------------------------------------------------------

        set_stage("code_generation")

        try:
            generated = self.generator.generate_code(spec)

        except Exception as exc:
            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                error=str(exc),
                stage="code_generation",
            )

        # ------------------------------------------------------
        # STATIC VALIDATION
        # ------------------------------------------------------

        set_stage("static_validation")

        try:
            self.validator.validate(
                generated.source,
                generated.spec,
            )

        except CapabilityValidationError as exc:
            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                error=str(exc),
                stage="static_validation",
            )

        except Exception as exc:
            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                error=str(exc),
                stage="static_validation",
            )

        # ------------------------------------------------------
        # SANDBOX EXECUTION
        # ------------------------------------------------------

        set_stage("sandbox_execution")

        try:
            sandbox_result = self.sandbox.run(generated)

        except SandboxExecutionError as exc:
            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                error=str(exc),
                stage="sandbox_startup",
            )

        except Exception as exc:
            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                error=str(exc),
                stage="sandbox_execution",
            )

        # ------------------------------------------------------
        # SANDBOX FAILED
        # ------------------------------------------------------

        if not sandbox_result.passed:
            diagnostics = (
                "Generated capability failed sandbox testing.\n"
                f"Exit code: {sandbox_result.exit_code}\n"
                f"Timed out: {sandbox_result.timed_out}\n"
                f"stdout:\n{sandbox_result.stdout}\n"
                f"stderr:\n{sandbox_result.stderr}"
            )

            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                sandbox_result=sandbox_result,
                error=diagnostics,
                stage="sandbox_execution",
            )

        # ------------------------------------------------------
        # SUCCESS
        # ------------------------------------------------------

        set_stage("completed")

        return CapabilityPipelineResult(
            passed=True,
            spec=spec,
            generated=generated,
            sandbox_result=sandbox_result,
            stage="completed",
        )
