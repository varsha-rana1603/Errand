import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of statically validating generated Python code.
    """

    valid: bool
    errors: list[str]


class StaticValidator:
    """
    Performs static safety checks on generated Python code.

    This validator does NOT execute the code.

    It is intentionally conservative: code is rejected when it
    uses modules, functions, or language features that Errand
    has not explicitly allowed.
    """

    ALLOWED_IMPORTS = {
        "webbrowser",
        "time",
    }

    BLOCKED_IMPORTS = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "shutil",
        "ctypes",
        "pathlib",
        "sys",
        "platform",
        "importlib",
        "pickle",
        "marshal",
        "builtins",
    }

    BLOCKED_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
    }

    BLOCKED_ATTRIBUTES = {
        "__globals__",
        "__builtins__",
        "__import__",
        "__code__",
        "__subclasses__",
        "__bases__",
        "__mro__",
    }

    def validate(self, source: str) -> ValidationResult:
        errors: list[str] = []

        try:
            tree = ast.parse(source)

        except SyntaxError as exc:
            return ValidationResult(
                valid=False,
                errors=[
                    f"Invalid Python syntax: {exc}"
                ],
            )

        for node in ast.walk(tree):

            self._check_import(node, errors)
            self._check_call(node, errors)
            self._check_attribute(node, errors)
            self._check_language_features(node, errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
        )

    def _check_import(
        self,
        node: ast.AST,
        errors: list[str],
    ) -> None:

        if isinstance(node, ast.Import):

            for alias in node.names:

                module = alias.name.split(".")[0]

                if module in self.BLOCKED_IMPORTS:

                    errors.append(
                        f"Blocked import: '{alias.name}'"
                    )

                elif module not in self.ALLOWED_IMPORTS:

                    errors.append(
                        f"Import not allowed: '{alias.name}'"
                    )

        elif isinstance(node, ast.ImportFrom):

            module = (node.module or "").split(".")[0]

            if module in self.BLOCKED_IMPORTS:

                errors.append(
                    f"Blocked import: '{node.module}'"
                )

            elif module not in self.ALLOWED_IMPORTS:

                errors.append(
                    f"Import not allowed: '{node.module}'"
                )

    def _check_call(
        self,
        node: ast.AST,
        errors: list[str],
    ) -> None:

        if not isinstance(node, ast.Call):
            return

        if isinstance(node.func, ast.Name):

            if node.func.id in self.BLOCKED_CALLS:

                errors.append(
                    f"Blocked function call: '{node.func.id}'"
                )

    def _check_attribute(
        self,
        node: ast.AST,
        errors: list[str],
    ) -> None:

        if not isinstance(node, ast.Attribute):
            return

        if node.attr in self.BLOCKED_ATTRIBUTES:

            errors.append(
                f"Blocked attribute access: '{node.attr}'"
            )

    def _check_language_features(
        self,
        node: ast.AST,
        errors: list[str],
    ) -> None:

        if isinstance(node, ast.Lambda):

            errors.append(
                "Lambda expressions are not allowed."
            )

        if isinstance(node, ast.Global):

            errors.append(
                "Global statements are not allowed."
            )

        if isinstance(node, ast.Nonlocal):

            errors.append(
                "Nonlocal statements are not allowed."
            )