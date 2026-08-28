import subprocess
import tempfile
from pathlib import Path

from errand.sandbox.result import SandboxResult


class SandboxRunner:
    """
    Executes untrusted Python code inside a temporary Docker container.

    The generated code never runs directly on the host machine.
    """

    def __init__(
        self,
        image: str = "python:3.14-slim",
        timeout: int = 10,
    ):
        self.image = image
        self.timeout = timeout

    def run(self, source: str) -> SandboxResult:
        """
        Execute Python source code inside Docker.

        ```
        The source is written to a temporary directory and mounted
        read-only into the container.
        """

        with tempfile.TemporaryDirectory() as temp_dir:

            source_path = Path(temp_dir) / "main.py"

            source_path.write_text(
                source,
                encoding="utf-8",
            )

            command = [
                "docker",
                "run",
                "--rm",

                # No network access.
                "--network",
                "none",

                # Prevent the container from gaining extra privileges.
                "--security-opt",
                "no-new-privileges",

                # Limit resources.
                "--cpus",
                "1",
                "--memory",
                "256m",

                # Mount generated code read-only.
                "-v",
                f"{source_path}:/sandbox/main.py:ro",

                self.image,
                "python",
                "/sandbox/main.py",
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

                stdout = (
                    exc.stdout.decode()
                    if isinstance(exc.stdout, bytes)
                    else (exc.stdout or "")
                )

                stderr = (
                    exc.stderr.decode()
                    if isinstance(exc.stderr, bytes)
                    else (exc.stderr or "")
                )

                return SandboxResult(
                    passed=False,
                    exit_code=-1,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=True,
                )

            return SandboxResult(
                passed=completed.returncode == 0,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
            )
