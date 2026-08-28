from errand.sandbox.runner import SandboxRunner


def test_sandbox_runs_python():

    runner = SandboxRunner()

    result = runner.run(
        """
print("hello from sandbox")
"""
    )

    assert result.passed is True
    assert result.exit_code == 0
    assert "hello from sandbox" in result.stdout


def test_sandbox_captures_failure():

    runner = SandboxRunner()

    result = runner.run(
        """
raise ValueError("intentional failure")
"""
    )

    assert result.passed is False
    assert result.exit_code != 0
    assert "intentional failure" in result.stderr


def test_sandbox_has_no_network():

    runner = SandboxRunner()

    result = runner.run(
        """
import urllib.request

urllib.request.urlopen(
    "https://example.com",
    timeout=2,
)
"""
    )

    assert result.passed is False


def test_sandbox_times_out():

    runner = SandboxRunner(timeout=1)

    result = runner.run(
        """
while True:
    pass
"""
    )

    assert result.passed is False
    assert result.timed_out is True