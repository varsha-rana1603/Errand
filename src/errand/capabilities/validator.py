import ast

from errand.capabilities.generator import GeneratedCapabilitySpec


class CapabilityValidationError(ValueError):
    """Raised when generated capability code is unsafe or invalid."""


class CapabilityValidator:
    """
    Statically validates generated capability source code.

    The validator uses a blacklist approach:
    legitimate Python/macOS imports are allowed by default,
    while known dangerous imports, calls, and reflective escape
    mechanisms are rejected.

    Generated code is still considered untrusted and MUST be
    sandbox-tested before registration or execution.
    """

    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "breakpoint",

        # Dangerous process/shell operations
        "system",
        "popen",
        "spawn",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",

        # Dangerous reflection / dynamic execution
        "execfile",
    }

    FORBIDDEN_MODULES = {
        "ctypes",
        "pickle",
        "marshal",
        "importlib",
        "code",
        "pty",
        "socket"
    }

    FORBIDDEN_ATTRIBUTES = {
        "__globals__",
        "__builtins__",
        "__code__",
        "__closure__",
        "__func__",
        "__subclasses__",
        "__bases__",
        "__mro__",
    }

    def validate(
        self,
        source: str,
        spec: GeneratedCapabilitySpec,
    ) -> None:

        if not source.strip():
            raise CapabilityValidationError(
                "Generated capability code is empty."
            )

        try:
            tree = ast.parse(source)

        except SyntaxError as exc:
            raise CapabilityValidationError(
                "Generated capability contains invalid Python: "
                f"{exc}"
            ) from exc

        self._validate_imports(tree)
        self._validate_calls(tree)
        self._validate_attributes(tree)
        self._validate_classes(tree, spec)

    # ----------------------------------------------------------
    # IMPORT VALIDATION
    # ----------------------------------------------------------

    def _validate_imports(self, tree: ast.AST) -> None:

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):

                for alias in node.names:

                    module = alias.name.split(".")[0]

                    if module in self.FORBIDDEN_MODULES:
                        raise CapabilityValidationError(
                            f"Import of '{alias.name}' is not allowed."
                        )

            elif isinstance(node, ast.ImportFrom):

                if node.module is None:
                    raise CapabilityValidationError(
                        "Relative imports are not allowed."
                    )

                module = node.module.split(".")[0]

                if module in self.FORBIDDEN_MODULES:
                    raise CapabilityValidationError(
                        f"Import of '{node.module}' is not allowed."
                    )

    # ----------------------------------------------------------
    # CALL VALIDATION
    # ----------------------------------------------------------

    def _validate_calls(self, tree: ast.AST) -> None:

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):

                if node.func.id in self.FORBIDDEN_CALLS:
                    raise CapabilityValidationError(
                        f"Call to '{node.func.id}()' is not allowed."
                    )

            elif isinstance(node.func, ast.Attribute):

                if node.func.attr in self.FORBIDDEN_CALLS:
                    raise CapabilityValidationError(
                        f"Call to '{node.func.attr}()' is not allowed."
                    )

    # ----------------------------------------------------------
    # ATTRIBUTE VALIDATION
    # ----------------------------------------------------------

    def _validate_attributes(self, tree: ast.AST) -> None:

        for node in ast.walk(tree):

            if not isinstance(node, ast.Attribute):
                continue

            if node.attr in self.FORBIDDEN_ATTRIBUTES:
                raise CapabilityValidationError(
                    f"Access to '{node.attr}' is not allowed."
                )

    # ----------------------------------------------------------
    # CAPABILITY STRUCTURE
    # ----------------------------------------------------------

    def _validate_classes(
        self,
        tree: ast.AST,
        spec: GeneratedCapabilitySpec,
    ) -> None:

        capability_classes = []

        for node in tree.body:

            if not isinstance(node, ast.ClassDef):
                continue

            for base in node.bases:

                if isinstance(base, ast.Name):

                    if base.id == "Capability":
                        capability_classes.append(node)

                elif isinstance(base, ast.Attribute):

                    if base.attr == "Capability":
                        capability_classes.append(node)

        if len(capability_classes) != 1:
            raise CapabilityValidationError(
                "Generated code must contain exactly one "
                "Capability subclass."
            )

        capability_class = capability_classes[0]

        methods = {
            node.name
            for node in capability_class.body
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        }

        required_methods = {
            "execute",
            "name",
            "description",
        }

        missing = required_methods - methods

        if missing:
            raise CapabilityValidationError(
                "Capability is missing required members: "
                f"{sorted(missing)}"
            )

        name_value = self._find_property_return(
            capability_class,
            "name",
        )

        if name_value != spec.name:
            raise CapabilityValidationError(
                f"Capability name '{name_value}' does not match "
                f"requested name '{spec.name}'."
            )

    @staticmethod
    def _find_property_return(
        class_node: ast.ClassDef,
        property_name: str,
    ) -> str | None:

        for node in class_node.body:

            if not isinstance(node, ast.FunctionDef):
                continue

            if node.name != property_name:
                continue

            is_property = any(
                (
                    isinstance(decorator, ast.Name)
                    and decorator.id == "property"
                )
                or (
                    isinstance(decorator, ast.Attribute)
                    and decorator.attr == "property"
                )
                for decorator in node.decorator_list
            )

            if not is_property:
                continue

            for child in ast.walk(node):

                if isinstance(child, ast.Return):

                    if isinstance(
                        child.value,
                        ast.Constant,
                    ):

                        if isinstance(
                            child.value.value,
                            str,
                        ):
                            return child.value.value

        return None