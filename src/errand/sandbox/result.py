from dataclasses import dataclass

@dataclass(frozen=True)
class SandboxResult:
    """
    Result of executing code inside the sandbox.
    """
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

