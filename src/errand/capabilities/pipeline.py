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

        def set_stage(stage: str) -> None:
            print(f"[PIPELINE] STAGE -> {stage}", flush=True)

            if stage_callback is not None:
                stage_callback(stage)

        print()
        print("=" * 70, flush=True)
        print("[PIPELINE] STARTING CAPABILITY PIPELINE", flush=True)
        print("=" * 70, flush=True)

        print(f"[PIPELINE] name = {name!r}", flush=True)
        print(f"[PIPELINE] description = {description!r}", flush=True)

        # ------------------------------------------------------
        # SPECIFICATION GENERATION
        # ------------------------------------------------------

        set_stage("specification_generation")

        try:
            print(
                "[PIPELINE] Calling generator.generate()...",
                flush=True,
            )

            spec = self.generator.generate(
                name=name,
                description=description,
            )

            print(
                "[PIPELINE] generator.generate() RETURNED",
                flush=True,
            )

            print(
                f"[PIPELINE] spec = {spec!r}",
                flush=True,
            )

        except Exception as exc:
            print(
                "[PIPELINE] SPECIFICATION GENERATION FAILED",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception: {type(exc).__name__}: {exc}",
                flush=True,
            )

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
            print(
                "[PIPELINE] Calling generator.generate_code()...",
                flush=True,
            )

            generated = self.generator.generate_code(spec)

            print(
                "[PIPELINE] generator.generate_code() RETURNED",
                flush=True,
            )

            print(
                f"[PIPELINE] generated = {generated!r}",
                flush=True,
            )

            print(
                f"[PIPELINE] generated.spec = {generated.spec!r}",
                flush=True,
            )

            print(
                f"[PIPELINE] generated.source length = "
                f"{len(generated.source)}",
                flush=True,
            )

        except Exception as exc:
            print(
                "[PIPELINE] CODE GENERATION FAILED",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception: {type(exc).__name__}: {exc}",
                flush=True,
            )

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

        print(
            "[PIPELINE] ABOUT TO CALL validator.validate()",
            flush=True,
        )

        print(
            "[PIPELINE] Validator:",
            repr(self.validator),
            flush=True,
        )

        print(
            "[PIPELINE] Source being validated:",
            flush=True,
        )

        print("-" * 70, flush=True)
        print(generated.source, flush=True)
        print("-" * 70, flush=True)

        print(
            "[PIPELINE] Specification being validated:",
            flush=True,
        )

        print(
            f"[PIPELINE] {generated.spec!r}",
            flush=True,
        )

        try:
            print(
                "[PIPELINE] ENTERING validator.validate()...",
                flush=True,
            )

            validation_result = self.validator.validate(
                generated.source,
                generated.spec,
            )

            print(
                "[PIPELINE] validator.validate() RETURNED",
                flush=True,
            )

            print(
                f"[PIPELINE] validation_result = "
                f"{validation_result!r}",
                flush=True,
            )

        except CapabilityValidationError as exc:
            print(
                "[PIPELINE] STATIC VALIDATION FAILED",
                flush=True,
            )

            print(
                f"[PIPELINE] Validation error: {exc}",
                flush=True,
            )

            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                error=str(exc),
                stage="static_validation",
            )

        except Exception as exc:
            print(
                "[PIPELINE] STATIC VALIDATION CRASHED",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception type: "
                f"{type(exc).__name__}",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception: {exc}",
                flush=True,
            )

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

        print(
            "[PIPELINE] ABOUT TO CALL sandbox.run()",
            flush=True,
        )

        print(
            f"[PIPELINE] Sandbox: {self.sandbox!r}",
            flush=True,
        )

        try:
            print(
                "[PIPELINE] ENTERING sandbox.run()...",
                flush=True,
            )

            sandbox_result = self.sandbox.run(generated)

            print(
                "[PIPELINE] sandbox.run() RETURNED",
                flush=True,
            )

            print(
                f"[PIPELINE] sandbox_result = "
                f"{sandbox_result!r}",
                flush=True,
            )

        except SandboxExecutionError as exc:
            print(
                "[PIPELINE] SANDBOX STARTUP FAILED",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception: {exc}",
                flush=True,
            )

            return CapabilityPipelineResult(
                passed=False,
                spec=spec,
                generated=generated,
                error=str(exc),
                stage="sandbox_startup",
            )

        except Exception as exc:
            print(
                "[PIPELINE] SANDBOX CRASHED",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception type: "
                f"{type(exc).__name__}",
                flush=True,
            )

            print(
                f"[PIPELINE] Exception: {exc}",
                flush=True,
            )

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

        print(
            f"[PIPELINE] sandbox_result.passed = "
            f"{sandbox_result.passed}",
            flush=True,
        )

        if not sandbox_result.passed:

            print(
                "[PIPELINE] SANDBOX TEST FAILED",
                flush=True,
            )

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

        print(
            "[PIPELINE] SANDBOX PASSED",
            flush=True,
        )

        set_stage("completed")

        print()
        print("=" * 70, flush=True)
        print("[PIPELINE] CAPABILITY PIPELINE COMPLETED SUCCESSFULLY", flush=True)
        print("=" * 70, flush=True)

        return CapabilityPipelineResult(
            passed=True,
            spec=spec,
            generated=generated,
            sandbox_result=sandbox_result,
            stage="completed",
        )