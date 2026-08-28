import json

import pytest

from errand.capabilities.base import Capability
from errand.capabilities.generator import (
    GeneratedCapability,
    GeneratedCapabilitySpec,
)
from errand.capabilities.registry import CapabilityRegistry
from errand.capabilities.validator import CapabilityValidator
from errand.capabilities.approval import (
    CapabilityApprovalError,
    CapabilityApprovalManager,
)


def make_spec(
    name="test_capability",
    description="A test capability.",
):
    return GeneratedCapabilitySpec(
        name=name,
        description=description,
        inputs={
            "message": "string",
        },
    )


def valid_source():
    return """
from errand.capabilities.base import Capability


class TestCapability(Capability):

    @property
    def name(self):
        return "test_capability"

    @property
    def description(self):
        return "A test capability."

    @property
    def input_schema(self):
        return {
            "message": str,
        }

    def execute(self, inputs):
        return inputs["message"]
"""


def make_generated(
    source=None,
    spec=None,
):
    if source is None:
        source = valid_source()

    if spec is None:
        spec = make_spec()

    return GeneratedCapability(
        spec=spec,
        source=source,
    )


def create_manager(tmp_path):
    registry = CapabilityRegistry()

    return CapabilityApprovalManager(
        registry=registry,
        storage_dir=tmp_path / "capabilities",
    )


def test_approval_requires_explicit_user_approval(tmp_path):

    manager = create_manager(tmp_path)

    generated = make_generated()

    with pytest.raises(CapabilityApprovalError):

        manager.approve(
            generated,
            approved=False,
        )


def test_approved_capability_is_registered(tmp_path):

    manager = create_manager(tmp_path)

    generated = make_generated()

    capability = manager.approve(
        generated,
        approved=True,
    )

    assert capability.name == "test_capability"

    registered = manager.registry.get(
        "test_capability"
    )

    assert registered is capability


def test_approval_persists_capability(tmp_path):

    manager = create_manager(tmp_path)

    generated = make_generated()

    manager.approve(
        generated,
        approved=True,
    )

    capability_dir = (
        tmp_path
        / "capabilities"
        / "test_capability"
    )

    source_path = capability_dir / "capability.py"
    spec_path = capability_dir / "spec.json"

    assert source_path.exists()
    assert spec_path.exists()

    assert source_path.read_text(
        encoding="utf-8"
    ) == generated.source

    persisted_spec = json.loads(
        spec_path.read_text(
            encoding="utf-8"
        )
    )

    assert persisted_spec == {
        "name": "test_capability",
        "description": "A test capability.",
        "inputs": {
            "message": "string",
        },
    }


def test_invalid_generated_code_cannot_be_approved(tmp_path):

    manager = create_manager(tmp_path)

    generated = make_generated(
        source=valid_source().replace(
            'return inputs["message"]',
            'return eval(inputs["message"])',
        )
    )

    with pytest.raises(CapabilityApprovalError):

        manager.approve(
            generated,
            approved=True,
        )

    with pytest.raises(Exception):

        manager.registry.get(
            "test_capability"
        )


def test_name_mismatch_cannot_be_approved(tmp_path):

    manager = create_manager(tmp_path)

    spec = make_spec(
        name="different_name",
    )

    generated = make_generated(
        spec=spec,
    )

    with pytest.raises(CapabilityApprovalError):

        manager.approve(
            generated,
            approved=True,
        )


def test_description_mismatch_cannot_be_approved(tmp_path):

    manager = create_manager(tmp_path)

    spec = make_spec(
        description="Different description.",
    )

    generated = make_generated(
        spec=spec,
    )

    with pytest.raises(CapabilityApprovalError):

        manager.approve(
            generated,
            approved=True,
        )


def test_input_schema_mismatch_cannot_be_approved(tmp_path):

    manager = create_manager(tmp_path)

    source = valid_source().replace(
        '"message": str',
        '"message": int',
    )

    generated = make_generated(
        source=source,
    )

    with pytest.raises(CapabilityApprovalError):

        manager.approve(
            generated,
            approved=True,
        )


def test_invalid_generated_object_cannot_be_approved(tmp_path):

    manager = create_manager(tmp_path)

    with pytest.raises(CapabilityApprovalError):

        manager.approve(
            "not a generated capability",
            approved=True,
        )


def test_persisted_capability_can_be_loaded(tmp_path):

    manager = create_manager(tmp_path)

    generated = make_generated()

    manager.approve(
        generated,
        approved=True,
    )

    new_registry = CapabilityRegistry()

    new_manager = CapabilityApprovalManager(
        registry=new_registry,
        storage_dir=(
            tmp_path / "capabilities"
        ),
    )

    loaded = new_manager.load_persisted()

    assert len(loaded) == 1

    capability = loaded[0]

    assert capability.name == "test_capability"
    assert capability.description == "A test capability."

    assert (
        new_registry.get("test_capability")
        is capability
    )


def test_missing_persisted_files_are_ignored(tmp_path):

    manager = create_manager(tmp_path)

    capability_dir = (
        tmp_path
        / "capabilities"
        / "broken_capability"
    )

    capability_dir.mkdir(
        parents=True,
    )

    (capability_dir / "capability.py").write_text(
        valid_source(),
        encoding="utf-8",
    )

    loaded = manager.load_persisted()

    assert loaded == []


def test_corrupted_persisted_spec_is_ignored(tmp_path):

    manager = create_manager(tmp_path)

    capability_dir = (
        tmp_path
        / "capabilities"
        / "broken_capability"
    )

    capability_dir.mkdir(
        parents=True,
    )

    (capability_dir / "capability.py").write_text(
        valid_source(),
        encoding="utf-8",
    )

    (capability_dir / "spec.json").write_text(
        "this is not json",
        encoding="utf-8",
    )

    loaded = manager.load_persisted()

    assert loaded == []


def test_duplicate_registered_capability_is_not_replaced(
    tmp_path,
):

    manager = create_manager(tmp_path)

    generated = make_generated()

    first = manager.approve(
        generated,
        approved=True,
    )

    new_registry = CapabilityRegistry()

    existing = type(
        "ExistingCapability",
        (Capability,),
        {
            "name": property(
                lambda self: "test_capability"
            ),
            "description": property(
                lambda self: "Existing capability."
            ),
            "execute": lambda self, inputs: "existing",
        },
    )()

    new_registry.register(existing)

    new_manager = CapabilityApprovalManager(
        registry=new_registry,
        storage_dir=(
            tmp_path / "capabilities"
        ),
    )

    loaded = new_manager.load_persisted()

    assert loaded == []

    assert (
        new_registry.get("test_capability")
        is existing
    )