from errand.sandbox.validator import StaticValidator


def test_validator_accepts_simple_python():

    validator = StaticValidator()

    result = validator.validate(
        """
def greet(name):
    return f"Hello {name}"

print(greet("Varsha"))
"""
    )

    assert result.valid is True
    assert result.errors == []


def test_validator_accepts_allowed_import():

    validator = StaticValidator()

    result = validator.validate(
        """
import webbrowser

webbrowser.open("https://example.com")
"""
    )

    assert result.valid is True


def test_validator_rejects_os_import():

    validator = StaticValidator()

    result = validator.validate(
        """
import os

os.system("whoami")
"""
    )

    assert result.valid is False
    assert any(
        "Blocked import" in error
        for error in result.errors
    )


def test_validator_rejects_subprocess():

    validator = StaticValidator()

    result = validator.validate(
        """
import subprocess

subprocess.run(["whoami"])
"""
    )

    assert result.valid is False


def test_validator_rejects_socket():

    validator = StaticValidator()

    result = validator.validate(
        """
import socket

socket.socket()
"""
    )

    assert result.valid is False


def test_validator_rejects_eval():

    validator = StaticValidator()

    result = validator.validate(
        """
value = eval("1 + 1")
"""
    )

    assert result.valid is False


def test_validator_rejects_exec():

    validator = StaticValidator()

    result = validator.validate(
        """
exec("print('hello')")
"""
    )

    assert result.valid is False


def test_validator_rejects_open():

    validator = StaticValidator()

    result = validator.validate(
        """
with open("secret.txt") as file:
    print(file.read())
"""
    )

    assert result.valid is False


def test_validator_rejects_global():

    validator = StaticValidator()

    result = validator.validate(
        """
global secret
secret = "value"
"""
    )

    assert result.valid is False


def test_validator_rejects_invalid_python():

    validator = StaticValidator()

    result = validator.validate(
        """
def broken(:
    pass
"""
    )

    assert result.valid is False
    assert len(result.errors) > 0