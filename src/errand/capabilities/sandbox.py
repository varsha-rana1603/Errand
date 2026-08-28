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


class SandboxExecutionError(RuntimeError):
    """Raised when the sandbox itself cannot be started."""


class CapabilitySandbox:
    """
    Executes generated capability code inside an isolated Docker
    container.

    The generated capability is NEVER executed directly on the host.

    The sandbox:
    - has no network access
    - has a read-only root filesystem
    - uses a temporary writable /tmp
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

        with tempfile.TemporaryDirectory(
            prefix="errand-sandbox-"
        ) as temp_dir:

            root = Path(temp_dir)

            self._create_project(
                root=root,
                generated=generated,
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

                return SandboxResult(
                    passed=False,
                    stdout=stdout,
                    stderr=(
                        stderr
                        + "\nSandbox execution timed out."
                    ),
                    exit_code=-1,
                )

            except FileNotFoundError as exc:

                raise SandboxExecutionError(
                    "Docker executable was not found."
                ) from exc

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

        base_source = """
class Capability:
    pass
"""

        test_source = f"""
import json
import sys
import traceback
import types


# ------------------------------------------------------------
# Create the minimal Errand package structure required by
# generated capabilities.
# ------------------------------------------------------------

errand_module = types.ModuleType("errand")

capabilities_module = types.ModuleType(
    "errand.capabilities"
)

base_module = types.ModuleType(
    "errand.capabilities.base"
)

base_module.Capability = type(
    "Capability",
    (),
    {{}},
)

sys.modules["errand"] = errand_module
sys.modules["errand.capabilities"] = capabilities_module
sys.modules["errand.capabilities.base"] = base_module


# ------------------------------------------------------------
# Load the generated capability.
# ------------------------------------------------------------

source_path = "/sandbox/capability.py"

namespace = {{}}

try:

    with open(
        source_path,
        "r",
        encoding="utf-8",
    ) as source_file:

        source = source_file.read()

    exec(
        compile(
            source,
            source_path,
            "exec",
        ),
        namespace,
    )

except Exception:

    print(
        "CAPABILITY_IMPORT_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


# ------------------------------------------------------------
# Find the Capability subclass.
# ------------------------------------------------------------

CapabilityBase = base_module.Capability

capability_classes = []

for value in namespace.values():

    if (
        isinstance(value, type)
        and issubclass(value, CapabilityBase)
        and value is not CapabilityBase
    ):
        capability_classes.append(value)


if len(capability_classes) != 1:

    print(
        "Expected exactly one Capability subclass.",
        file=sys.stderr,
    )

    sys.exit(1)


CapabilityClass = capability_classes[0]


# ------------------------------------------------------------
# Instantiate.
# ------------------------------------------------------------

try:

    capability = CapabilityClass()

except Exception:

    print(
        "CAPABILITY_INSTANTIATION_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


# ------------------------------------------------------------
# Validate required interface.
# ------------------------------------------------------------

required = [
    "name",
    "description",
    "input_schema",
    "execute",
]

for member in required:

    if not hasattr(capability, member):

        print(
            f"Missing required capability member: {{member}}",
            file=sys.stderr,
        )

        sys.exit(1)


# ------------------------------------------------------------
# Validate metadata.
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Construct safe test inputs.
#
# We don't know the actual capability's required values,
# so primitive placeholder values are generated from its
# declared input schema.
# ------------------------------------------------------------

test_inputs = {{}}

for input_name, input_type in input_schema.items():

    if input_type is str:

        test_inputs[input_name] = "sandbox_test"

    elif input_type is int:

        test_inputs[input_name] = 1

    elif input_type is float:

        test_inputs[input_name] = 1.0

    elif input_type is bool:

        test_inputs[input_name] = False

    else:

        print(
            (
                f"Unsupported input type for sandbox test: "
                f"{{input_name}}"
            ),
            file=sys.stderr,
        )

        sys.exit(1)


# ------------------------------------------------------------
# Execute capability.
# ------------------------------------------------------------

try:

    result = capability.execute(test_inputs)

except Exception:

    print(
        "CAPABILITY_EXECUTION_FAILED",
        file=sys.stderr,
    )

    traceback.print_exc()

    sys.exit(1)


# ------------------------------------------------------------
# Success.
# ------------------------------------------------------------

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

sys.exit(0)
"""

        (root / "capability.py").write_text(
            capability_source,
            encoding="utf-8",
        )

        (root / "base.py").write_text(
            base_source,
            encoding="utf-8",
        )

        (root / "test_capability.py").write_text(
            test_source,
            encoding="utf-8",
        )