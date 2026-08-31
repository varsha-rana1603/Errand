import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from errand.capabilities.generator import GeneratedCapability


@dataclass(frozen=True)
class SandboxResult:
    """
    Result of executing a generated capability inside Docker.
    """

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """
        Backwards-compatible alias for passed.
        """
        return self.passed


class SandboxExecutionError(RuntimeError):
    """Raised when the sandbox itself cannot be started."""


class CapabilitySandbox:
    """
    Executes generated capability code inside an isolated Docker
    container.

    Generated code is NEVER executed directly on the host.

    The sandbox:
    - has no network access
    - has a read-only root filesystem
    - has a temporary writable /tmp
    - limits memory
    - limits CPU
    - limits processes
    - drops Linux capabilities
    - prevents privilege escalation
    - removes the container after execution
    """

    IMAGE = "python:3.14-slim"

    def __init__(
        self,
        timeout: int = 20,
        memory: str = "256m",
        cpus: str = "1.0",
        pids_limit: int = 64,
    ):
        self.timeout = timeout
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit

    def run(
        self,
        generated: GeneratedCapability,
    ) -> SandboxResult:

        print()
        print("=" * 70, flush=True)
        print("[SANDBOX] STARTING SANDBOX", flush=True)
        print("=" * 70, flush=True)

        print(
            f"[SANDBOX] Generated capability name: "
            f"{generated.spec.name}",
            flush=True,
        )

        print(
            f"[SANDBOX] Generated capability description: "
            f"{generated.spec.description}",
            flush=True,
        )

        print(
            f"[SANDBOX] Generated specification inputs: "
            f"{generated.spec.inputs}",
            flush=True,
        )

        print(
            f"[SANDBOX] Generated specification input types: "
            f"{ {k: type(v).__name__ for k, v in generated.spec.inputs.items()} }",
            flush=True,
        )

        print(
            f"[SANDBOX] Generated source length: "
            f"{len(generated.source)}",
            flush=True,
        )

        print()
        print(
            "[SANDBOX] SOURCE RECEIVED BY SANDBOX:",
            flush=True,
        )

        print("-" * 70, flush=True)
        print(generated.source, flush=True)
        print("-" * 70, flush=True)

        with tempfile.TemporaryDirectory(
            prefix="errand-sandbox-"
        ) as temp_dir:

            root = Path(temp_dir)

            print(
                f"[SANDBOX] Temporary sandbox directory: {root}",
                flush=True,
            )

            print()
            print(
                "[SANDBOX] CREATING PROJECT",
                flush=True,
            )

            self._create_project(
                root=root,
                generated=generated,
            )

            print(
                "[SANDBOX] Project creation complete.",
                flush=True,
            )

            print(
                f"[SANDBOX] capability.py written to: "
                f"{root / 'capability.py'}",
                flush=True,
            )

            print(
                f"[SANDBOX] test_capability.py written to: "
                f"{root / 'test_capability.py'}",
                flush=True,
            )

            command = [
                "docker",
                "run",
                "--rm",

                # No network access.
                "--network",
                "none",

                # Read-only container filesystem.
                "--read-only",

                # Temporary writable filesystem.
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",

                # Resource limits.
                "--memory",
                self.memory,

                "--cpus",
                self.cpus,

                "--pids-limit",
                str(self.pids_limit),

                # Drop Linux capabilities.
                "--cap-drop",
                "ALL",

                # Prevent privilege escalation.
                "--security-opt",
                "no-new-privileges",

                # Mount generated project read-only.
                "-v",
                f"{root}:/sandbox:ro",

                self.IMAGE,

                "python",
                "/sandbox/test_capability.py",
            ]

            print()
            print(
                "[SANDBOX] DOCKER COMMAND:",
                flush=True,
            )

            print("-" * 70, flush=True)
            print(
                " ".join(command),
                flush=True,
            )
            print("-" * 70, flush=True)

            try:

                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )

            except subprocess.TimeoutExpired as exc:

                stdout = exc.stdout or ""
                stderr = exc.stderr or ""

                if isinstance(stdout, bytes):
                    stdout = stdout.decode(
                        "utf-8",
                        errors="replace",
                    )

                if isinstance(stderr, bytes):
                    stderr = stderr.decode(
                        "utf-8",
                        errors="replace",
                    )

                print()
                print(
                    "[SANDBOX] DOCKER TIMED OUT",
                    flush=True,
                )

                return SandboxResult(
                    passed=False,
                    stdout=stdout,
                    stderr=(
                        stderr
                        + "\nSandbox execution timed out."
                    ),
                    exit_code=-1,
                    timed_out=True,
                )

            except FileNotFoundError as exc:

                print(
                    "[SANDBOX] DOCKER EXECUTABLE NOT FOUND",
                    flush=True,
                )

                raise SandboxExecutionError(
                    "Docker executable was not found."
                ) from exc

            print()
            print(
                "[SANDBOX] DOCKER FINISHED",
                flush=True,
            )

            print("-" * 70, flush=True)

            print(
                f"[SANDBOX] Exit code: "
                f"{completed.returncode}",
                flush=True,
            )

            print(
                f"[SANDBOX] Passed: "
                f"{completed.returncode == 0}",
                flush=True,
            )

            print()
            print(
                "[SANDBOX] STDOUT:",
                flush=True,
            )

            print(
                completed.stdout,
                flush=True,
            )

            print()
            print(
                "[SANDBOX] STDERR:",
                flush=True,
            )

            print(
                completed.stderr,
                flush=True,
            )

            print("-" * 70, flush=True)

            return SandboxResult(
                passed=completed.returncode == 0,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
            )

    @staticmethod
    def _create_project(
        root: Path,
        generated: GeneratedCapability,
    ) -> None:

        capability_source = generated.source

        # --------------------------------------------------------
        # AUTHORITATIVE CONTRACT
        # --------------------------------------------------------

        expected_name = generated.spec.name
        expected_description = generated.spec.description
        expected_inputs = generated.spec.inputs

        print(
            "[SANDBOX] expected_name:",
            repr(expected_name),
            flush=True,
        )

        print(
            "[SANDBOX] expected_description:",
            repr(expected_description),
            flush=True,
        )

        print(
            "[SANDBOX] expected_inputs:",
            repr(expected_inputs),
            flush=True,
        )

        print(
            "[SANDBOX] expected_inputs types:",
            {
                key: type(value).__name__
                for key, value in expected_inputs.items()
            },
            flush=True,
        )

        base_source = """
class Capability:
    pass
"""

        # --------------------------------------------------------
        # IMPORTANT
        #
        # This is an f-string.
        #
        # Therefore values inserted using {value!r} must NOT
        # themselves be wrapped in f"..." or additional quotes.
        # --------------------------------------------------------

        test_source = f"""
import json
import sys
import traceback
import types


print("=" * 70)
print("[DOCKER] SANDBOX TEST STARTED")
print("=" * 70)


# ============================================================
# EXPECTED CONTRACT
# ============================================================

EXPECTED_NAME = {expected_name!r}

EXPECTED_DESCRIPTION = {expected_description!r}

EXPECTED_INPUTS = {expected_inputs!r}


print(
    "[DOCKER] EXPECTED_NAME:",
    repr(EXPECTED_NAME),
)

print(
    "[DOCKER] EXPECTED_DESCRIPTION:",
    repr(EXPECTED_DESCRIPTION),
)

print(
    "[DOCKER] EXPECTED_INPUTS:",
    repr(EXPECTED_INPUTS),
)

print(
    "[DOCKER] EXPECTED_INPUTS TYPES:",
    {{
        key: type(value).__name__
        for key, value in EXPECTED_INPUTS.items()
    }},
)


# ============================================================
# MINIMAL ERRAND PACKAGE
# ============================================================

errand_module = types.ModuleType("errand")

capabilities_module = types.ModuleType(
    "errand.capabilities"
)

base_module = types.ModuleType(
    "errand.capabilities.base"
)


class Capability:
    pass


base_module.Capability = Capability


sys.modules["errand"] = errand_module
sys.modules["errand.capabilities"] = capabilities_module
sys.modules["errand.capabilities.base"] = base_module


# ============================================================
# LOAD GENERATED CAPABILITY
# ============================================================

source_path = "/sandbox/capability.py"

namespace = {{}}

try:

    with open(
        source_path,
        "r",
        encoding="utf-8",
    ) as source_file:

        source = source_file.read()

    print()
    print(
        "[DOCKER] SOURCE READ FROM /sandbox/capability.py:"
    )

    print("-" * 70)
    print(source)
    print("-" * 70)

    print(
        "[DOCKER] SOURCE LENGTH:",
        len(source),
    )

    exec(
        compile(
            source,
            source_path,
            "exec",
        ),
        namespace,
    )

    print(
        "[DOCKER] Generated source executed successfully."
    )

except Exception:

    print(
        "CAPABILITY_IMPORT_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


# ============================================================
# FIND CAPABILITY CLASS
# ============================================================

CapabilityBase = base_module.Capability

capability_classes = []

for value in namespace.values():

    if (
        isinstance(value, type)
        and issubclass(value, CapabilityBase)
        and value is not CapabilityBase
    ):
        capability_classes.append(value)


print(
    "[DOCKER] Capability classes found:",
    capability_classes,
)


if len(capability_classes) != 1:

    print(
        (
            "Expected exactly one Capability subclass. "
            f"Found {{len(capability_classes)}}."
        ),
        file=sys.stderr,
    )

    sys.exit(1)


CapabilityClass = capability_classes[0]

print(
    "[DOCKER] Capability class:",
    CapabilityClass,
)


# ============================================================
# INSTANTIATE
# ============================================================

try:

    capability = CapabilityClass()

    print(
        "[DOCKER] Capability instantiated successfully."
    )

except Exception:

    print(
        "CAPABILITY_INSTANTIATION_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


# ============================================================
# REQUIRED INTERFACE
# ============================================================

required = [
    "name",
    "description",
    "input_schema",
    "execute",
]

for member in required:

    print(
        f"[DOCKER] Checking required member: {{member}}"
    )

    if not hasattr(capability, member):

        print(
            f"Missing required capability member: {{member}}",
            file=sys.stderr,
        )

        sys.exit(1)


# ============================================================
# READ METADATA
# ============================================================

try:

    name = capability.name
    description = capability.description
    input_schema = capability.input_schema

except Exception:

    print(
        "CAPABILITY_METADATA_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


print()
print("[DOCKER] ACTUAL CAPABILITY METADATA")

print(
    "[DOCKER] name:",
    repr(name),
)

print(
    "[DOCKER] description:",
    repr(description),
)

print(
    "[DOCKER] input_schema:",
    repr(input_schema),
)

print(
    "[DOCKER] input_schema types:",
    {{
        key: type(value).__name__
        for key, value in input_schema.items()
    }},
)


# ============================================================
# BASIC TYPE VALIDATION
# ============================================================

if not isinstance(name, str) or not name.strip():

    print(
        "Capability name must be a non-empty string.",
        file=sys.stderr,
    )

    sys.exit(1)


if not isinstance(description, str):

    print(
        "Capability description must be a string.",
        file=sys.stderr,
    )

    sys.exit(1)


if not isinstance(input_schema, dict):

    print(
        "Capability input_schema must be a dictionary.",
        file=sys.stderr,
    )

    sys.exit(1)


# ============================================================
# CONTRACT VALIDATION
# ============================================================

print()
print("[DOCKER] CONTRACT COMPARISON")

print(
    "[DOCKER] EXPECTED:",
    repr(EXPECTED_INPUTS),
)

print(
    "[DOCKER] ACTUAL:",
    repr(input_schema),
)

print(
    "[DOCKER] EXPECTED == ACTUAL:",
    input_schema == EXPECTED_INPUTS,
)


if name != EXPECTED_NAME:

    print(
        (
            "Capability name does not match the generated "
            "specification.\\n"
            f"Expected: {{EXPECTED_NAME!r}}\\n"
            f"Got: {{name!r}}"
        ),
        file=sys.stderr,
    )

    sys.exit(1)


if description != EXPECTED_DESCRIPTION:

    print(
        (
            "Capability description does not match the "
            "generated specification.\\n"
            f"Expected: {{EXPECTED_DESCRIPTION!r}}\\n"
            f"Got: {{description!r}}"
        ),
        file=sys.stderr,
    )

    sys.exit(1)


if input_schema != EXPECTED_INPUTS:

    print(
        (
            "Capability input_schema does not match the "
            "generated specification.\\n"
            f"Expected: {{EXPECTED_INPUTS!r}}\\n"
            f"Got: {{input_schema!r}}"
        ),
        file=sys.stderr,
    )

    sys.exit(1)


print(
    "[DOCKER] CONTRACT VALIDATION PASSED"
)


# ============================================================
# BUILD TEST INPUTS
# ============================================================

test_inputs = {{}}

for input_name, input_type in input_schema.items():

    print(
        f"[DOCKER] Building test input: "
        f"{{input_name}} -> {{input_type!r}}"
    )

    if input_type == "string":

        test_inputs[input_name] = "sandbox_test"

    elif input_type == "integer":

        test_inputs[input_name] = 1

    elif input_type == "float":

        test_inputs[input_name] = 1.0

    elif input_type == "boolean":

        test_inputs[input_name] = False

    else:

        print(
            (
                "Unsupported input type for sandbox test: "
                f"{{input_name}} -> {{input_type!r}}"
            ),
            file=sys.stderr,
        )

        sys.exit(1)


print(
    "[DOCKER] TEST INPUTS:",
    repr(test_inputs),
)


# ============================================================
# EXECUTE
# ============================================================

print(
    "[DOCKER] Executing capability..."
)

try:

    result = capability.execute(test_inputs)

    print(
        "[DOCKER] Capability execution returned successfully."
    )

    print(
        "[DOCKER] Result:",
        repr(result),
    )

except Exception:

    print(
        "CAPABILITY_EXECUTION_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


# ============================================================
# SUCCESS
# ============================================================

print(
    json.dumps(
        {{
            "status": "passed",
            "name": name,
            "result_type": type(result).__name__,
            "result": str(result),
        }}
    )
)

print(
    "[DOCKER] SANDBOX TEST PASSED"
)

sys.exit(0)
"""

        print(
            "[SANDBOX] Writing capability.py...",
            flush=True,
        )

        (root / "capability.py").write_text(
            capability_source,
            encoding="utf-8",
        )

        print(
            "[SANDBOX] Writing base.py...",
            flush=True,
        )

        (root / "base.py").write_text(
            base_source,
            encoding="utf-8",
        )

        print(
            "[SANDBOX] Writing test_capability.py...",
            flush=True,
        )

        (root / "test_capability.py").write_text(
            test_source,
            encoding="utf-8",
        )

        # --------------------------------------------------------
        # DEBUG: PRINT THE GENERATED TEST FILE
        # --------------------------------------------------------

        print()
        print(
            "[SANDBOX] GENERATED test_capability.py:",
            flush=True,
        )

        print("-" * 70, flush=True)
        print(test_source, flush=True)
        print("-" * 70, flush=True)