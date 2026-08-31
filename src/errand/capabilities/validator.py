import ast

from errand.capabilities.generator import GeneratedCapabilitySpec


class CapabilityValidationError(ValueError):
    """Raised when generated capability code is unsafe or invalid."""


class CapabilityValidator:
    """
    Statically validates generated capability source code.

    Generated code is untrusted and MUST be sandbox-tested
    before registration or execution.
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
        "socket",
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

        print("[VALIDATOR] Starting static validation...")

        if not source.strip():
            raise CapabilityValidationError(
                "Generated capability code is empty."
            )

        print("[VALIDATOR] Parsing Python AST...")

        try:
            tree = ast.parse(source)

        except SyntaxError as exc:
            raise CapabilityValidationError(
                "Generated capability contains invalid Python: "
                f"{exc}"
            ) from exc

        print("[VALIDATOR] AST parsing passed.")

        print("[VALIDATOR] Checking imports...")
        self._validate_imports(tree)
        print("[VALIDATOR] Import validation passed.")

        print("[VALIDATOR] Checking dangerous calls...")
        self._validate_calls(tree)
        print("[VALIDATOR] Call validation passed.")

        print("[VALIDATOR] Checking dangerous attributes...")
        self._validate_attributes(tree)
        print("[VALIDATOR] Attribute validation passed.")

        print("[VALIDATOR] Checking capability structure...")
        self._validate_classes(tree, spec)
        print("[VALIDATOR] Capability structure validation passed.")

        print("[VALIDATOR] ✓ STATIC VALIDATION PASSED")

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

        print(
            "[VALIDATOR] Capability subclasses found:",
            len(capability_classes),
        )

        if len(capability_classes) != 1:
            raise CapabilityValidationError(
                "Generated code must contain exactly one "
                "Capability subclass."
            )

        capability_class = capability_classes[0]

        print(
            "[VALIDATOR] Capability class:",
            capability_class.name,
        )

        # ------------------------------------------------------
        # REQUIRED METHODS
        # ------------------------------------------------------

        methods = {
            node.name
            for node in capability_class.body
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        }

        print(
            "[VALIDATOR] Methods found:",
            sorted(methods),
        )

        required_methods = {
            "execute",
            "name",
            "description",
            "input_schema",
        }

        missing = required_methods - methods

        if missing:
            raise CapabilityValidationError(
                "Capability is missing required members: "
                f"{sorted(missing)}"
            )

        # ------------------------------------------------------
        # PROPERTY VALIDATION
        # ------------------------------------------------------

        for property_name in (
            "name",
            "description",
            "input_schema",
        ):

            print(
                f"[VALIDATOR] Checking @{property_name} property..."
            )

            if not self._is_property(
                capability_class,
                property_name,
            ):
                raise CapabilityValidationError(
                    f"Capability member '{property_name}' "
                    "must be implemented as an @property."
                )

        # ------------------------------------------------------
        # NAME VALIDATION
        # ------------------------------------------------------

        name_value = self._find_property_return(
            capability_class,
            "name",
        )

        print(
            "[VALIDATOR] Generated name:",
            repr(name_value),
        )

        print(
            "[VALIDATOR] Expected name:",
            repr(spec.name),
        )

        if name_value != spec.name:
            raise CapabilityValidationError(
                f"Capability name '{name_value}' does not match "
                f"requested name '{spec.name}'."
            )

        # ------------------------------------------------------
        # DESCRIPTION VALIDATION
        # ------------------------------------------------------

        description_value = self._find_property_return(
            capability_class,
            "description",
        )

        if description_value != spec.description:
            raise CapabilityValidationError(
                "Capability description does not match "
                "the generated specification."
            )

        # ------------------------------------------------------
        # INPUT SCHEMA VALIDATION
        # ------------------------------------------------------

        input_schema = self._find_dict_property_return(
            capability_class,
            "input_schema",
        )

        print(
            "[VALIDATOR] Generated input_schema:",
            repr(input_schema),
        )

        print(
            "[VALIDATOR] Expected input_schema:",
            repr(spec.inputs),
        )

        if input_schema != spec.inputs:
            print("IINPUT_SCHEMA:", input_schema, spec.inputs)
            raise CapabilityValidationError(
                "Capability input_schema does not match "
                "the generated specification."
            )

    # ----------------------------------------------------------
    # PROPERTY DETECTION
    # ----------------------------------------------------------

    @staticmethod
    def _is_property(
        class_node: ast.ClassDef,
        property_name: str,
    ) -> bool:

        for node in class_node.body:

            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            if node.name != property_name:
                continue

            for decorator in node.decorator_list:

                if (
                    isinstance(decorator, ast.Name)
                    and decorator.id == "property"
                ):
                    return True

                if (
                    isinstance(decorator, ast.Attribute)
                    and decorator.attr == "property"
                ):
                    return True

        return False

    # ----------------------------------------------------------
    # STRING PROPERTY RETURN
    # ----------------------------------------------------------

    @staticmethod
    def _find_property_return(
        class_node: ast.ClassDef,
        property_name: str,
    ) -> str | None:

        for node in class_node.body:

            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            if node.name != property_name:
                continue

            if not CapabilityValidator._is_property(
                class_node,
                property_name,
            ):
                return None

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

    # ----------------------------------------------------------
    # DICT PROPERTY RETURN
    # ----------------------------------------------------------

    @staticmethod
    def _find_dict_property_return(
        class_node: ast.ClassDef,
        property_name: str,
    ) -> dict | None:

        for node in class_node.body:

            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            if node.name != property_name:
                continue

            if not CapabilityValidator._is_property(
                class_node,
                property_name,
            ):
                return None

            for child in ast.walk(node):

                if not isinstance(child, ast.Return):
                    continue

                if not isinstance(child.value, ast.Dict):
                    continue

                result = {}

                for key, value in zip(
                    child.value.keys,
                    child.value.values,
                ):

                    if not isinstance(
                        key,
                        ast.Constant,
                    ):
                        return None

                    if not isinstance(
                        key.value,
                        str,
                    ):
                        return None

                    if not isinstance(
                        value,
                        ast.Constant,
                    ):
                        return None

                    if not isinstance(
                        value.value,
                        str,
                    ):
                        return None

                    result[key.value] = value.value

                return result

        return None