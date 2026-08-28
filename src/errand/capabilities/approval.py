# Capability Approval and Persistences
import ast
import json
from pathlib import Path

from errand.capabilities.base import Capability
from errand.capabilities.generator import (
    GeneratedCapability,
    GeneratedCapabilitySpec,
)
from errand.capabilities.registry import CapabilityRegistry
from errand.capabilities.validator import CapabilityValidator


class CapabilityApprovalError(RuntimeError):
    """Raised when an untrusted capability cannot be approved."""


class CapabilityApprovalManager:
    """
    Controls the boundary between generated capabilities and the
    trusted CapabilityRegistry.

    A capability may enter the registry only when:

        1. It was successfully generated.
        2. Static validation has passed.
        3. The caller explicitly approves it.
        4. Its implementation matches its specification.

    Approved capabilities are persisted under:

        ~/.errand/capabilities/

    Generated code never writes to Errand's source tree.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        validator: CapabilityValidator | None = None,
        storage_dir: Path | None = None,
    ):
        self.registry = registry

        self.validator = (
            validator
            if validator is not None
            else CapabilityValidator()
        )

        self.storage_dir = (
            storage_dir
            if storage_dir is not None
            else Path.home() / ".errand" / "capabilities"
        )

    # ----------------------------------------------------------
    # APPROVAL
    # ----------------------------------------------------------

    def approve(
        self,
        generated: GeneratedCapability,
        approved: bool,
    ) -> Capability:
        """
        Approve and register a generated capability.

        The caller must explicitly pass approved=True.

        The generated source is statically validated again here,
        even if it already passed through the generation pipeline.

        Returns the newly registered trusted Capability.
        """

        if not approved:
            raise CapabilityApprovalError(
                "Capability approval was not granted by the user."
            )

        if not isinstance(generated, GeneratedCapability):
            raise CapabilityApprovalError(
                "Invalid generated capability."
            )

        # Defense in depth:
        # validate again immediately before crossing the trust boundary.
        try:
            self.validator.validate(
                generated.source,
                generated.spec,
            )

        except Exception as exc:
            raise CapabilityApprovalError(
                f"Capability failed final validation: {exc}"
            ) from exc

        capability = self._load_from_source(
            generated.source,
            generated.spec,
        )

        # Persist only after the capability has been completely
        # validated and instantiated successfully.
        self._persist(
            generated=generated,
        )

        # Only now does generated code enter the trusted registry.
        try:
            self.registry.register(capability)

        except Exception:
            # Registration failed. We deliberately do not silently
            # replace an existing trusted capability.
            raise

        return capability

    # ----------------------------------------------------------
    # SOURCE LOADING
    # ----------------------------------------------------------

    def _load_from_source(
        self,
        source: str,
        spec: GeneratedCapabilitySpec,
    ) -> Capability:
        """
        Load a validated capability source into an isolated namespace.

        This method must only be called after validation.
        """

        namespace = {
            "__name__": (
                f"errand.generated.{spec.name}"
            ),
        }

        try:
            tree = ast.parse(source)

            compiled = compile(
                tree,
                f"<generated:{spec.name}>",
                "exec",
            )

            exec(
                compiled,
                namespace,
            )

        except Exception as exc:
            raise CapabilityApprovalError(
                f"Failed to load approved capability "
                f"'{spec.name}': {exc}"
            ) from exc

        capability_classes = []

        for value in namespace.values():

            if not isinstance(value, type):
                continue

            if value is Capability:
                continue

            try:
                is_capability = issubclass(
                    value,
                    Capability,
                )
            except TypeError:
                is_capability = False

            if is_capability:
                capability_classes.append(value)

        if len(capability_classes) != 1:
            raise CapabilityApprovalError(
                "Approved capability source must contain exactly "
                "one Capability subclass."
            )

        capability_class = capability_classes[0]

        try:
            capability = capability_class()
        except Exception as exc:
            raise CapabilityApprovalError(
                f"Failed to instantiate capability "
                f"'{spec.name}': {exc}"
            ) from exc

        self._verify_capability(
            capability=capability,
            spec=spec,
        )

        return capability

    # ----------------------------------------------------------
    # VERIFICATION
    # ----------------------------------------------------------

    @staticmethod
    def _verify_capability(
        capability: Capability,
        spec: GeneratedCapabilitySpec,
    ) -> None:
        """
        Verify that the implementation actually matches the
        generated specification before registration.
        """

        if capability.name != spec.name:
            raise CapabilityApprovalError(
                f"Capability name '{capability.name}' does not "
                f"match specification '{spec.name}'."
            )

        if capability.description != spec.description:
            raise CapabilityApprovalError(
                "Capability description does not match "
                "the generated specification."
            )

        schema = capability.input_schema

        if not isinstance(schema, dict):
            raise CapabilityApprovalError(
                "Capability input_schema must be a dictionary."
            )

        expected_types = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
        }

        expected_schema = {
            name: expected_types[input_type]
            for name, input_type in spec.inputs.items()
        }

        if schema != expected_schema:
            raise CapabilityApprovalError(
                "Capability input_schema does not match "
                "the generated specification."
            )

        if not callable(capability.execute):
            raise CapabilityApprovalError(
                "Capability execute() is not callable."
            )

    # ----------------------------------------------------------
    # PERSISTENCE
    # ----------------------------------------------------------

    def _persist(
        self,
        generated: GeneratedCapability,
    ) -> Path:
        """
        Persist an approved capability.

        Each capability gets its own directory:

            ~/.errand/capabilities/<name>/
                capability.py
                spec.json
        """

        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        capability_dir = (
            self.storage_dir / generated.spec.name
        )

        capability_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_path = capability_dir / "capability.py"
        spec_path = capability_dir / "spec.json"

        source_path.write_text(
            generated.source,
            encoding="utf-8",
        )

        spec_data = {
            "name": generated.spec.name,
            "description": generated.spec.description,
            "inputs": generated.spec.inputs,
        }

        spec_path.write_text(
            json.dumps(
                spec_data,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        return capability_dir

    # ----------------------------------------------------------
    # STARTUP LOADING
    # ----------------------------------------------------------

    def load_persisted(self) -> list[Capability]:
        """
        Load previously approved capabilities.

        Every persisted capability is statically validated again
        before it can enter the trusted registry.

        Returns the capabilities successfully loaded.
        """

        if not self.storage_dir.exists():
            return []

        loaded = []

        for capability_dir in sorted(
            self.storage_dir.iterdir()
        ):

            if not capability_dir.is_dir():
                continue

            source_path = (
                capability_dir / "capability.py"
            )

            spec_path = (
                capability_dir / "spec.json"
            )

            if not source_path.exists():
                continue

            if not spec_path.exists():
                continue

            try:
                spec = self._read_spec(
                    spec_path,
                )

                source = source_path.read_text(
                    encoding="utf-8",
                )

                # Revalidate persisted code before trusting it.
                self.validator.validate(
                    source,
                    spec,
                )

                capability = self._load_from_source(
                    source,
                    spec,
                )

                # Do not replace an existing trusted capability.
                try:
                    self.registry.register(
                        capability,
                    )
                except ValueError:
                    continue

                loaded.append(capability)

            except Exception:
                # A corrupted or invalid persisted capability must
                # never prevent Errand itself from starting.
                continue

        return loaded

    @staticmethod
    def _read_spec(
        path: Path,
    ) -> GeneratedCapabilitySpec:
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except Exception as exc:
            raise CapabilityApprovalError(
                f"Invalid persisted capability specification: "
                f"{exc}"
            ) from exc

        if not isinstance(data, dict):
            raise CapabilityApprovalError(
                "Persisted capability specification "
                "must be a JSON object."
            )

        name = data.get("name")
        description = data.get("description")
        inputs = data.get("inputs")

        if not isinstance(name, str) or not name.strip():
            raise CapabilityApprovalError(
                "Persisted capability has an invalid name."
            )

        if not isinstance(description, str):
            raise CapabilityApprovalError(
                "Persisted capability has an invalid description."
            )

        if not isinstance(inputs, dict):
            raise CapabilityApprovalError(
                "Persisted capability inputs must be an object."
            )

        return GeneratedCapabilitySpec(
            name=name,
            description=description,
            inputs=inputs,
        )
