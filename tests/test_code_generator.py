from errand.capabilities.code_generator import (
    CapabilityCodeGenerator,
    GeneratedCapabilityCode,
)
from errand.capabilities.generator import GeneratedCapabilitySpec


def test_generated_capability_code_has_expected_structure(
    monkeypatch,
):

    spec = GeneratedCapabilitySpec(
        name="play_music",
        description="Play a requested song using a music service.",
        inputs={
            "song": "string",
            "artist": "string",
        },
    )

    class FakeResponse:
        text = """
from errand.capabilities.base import Capability


class PlayMusicCapability(Capability):

    @property
    def name(self) -> str:
        return "play_music"

    @property
    def description(self) -> str:
        return "Play a requested song."

    @property
    def input_schema(self) -> dict[str, type]:
        return {
            "song": str,
            "artist": str,
        }

    def execute(self, inputs: dict) -> object:
        return "Playing song."
"""

    class FakeModels:

        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    generator = CapabilityCodeGenerator.__new__(
        CapabilityCodeGenerator
    )

    generator.model = "test"
    generator.client = FakeClient()

    result = generator.generate(spec)

    assert isinstance(result, GeneratedCapabilityCode)

    assert result.name == "play_music"

    assert "class PlayMusicCapability" in result.source
    assert "from errand.capabilities.base import Capability" in result.source
    assert 'return "play_music"' in result.source


def test_generated_code_fences_are_removed():

    source = """```python
from errand.capabilities.base import Capability


class TestCapability(Capability):
    pass
```"""

    result = CapabilityCodeGenerator._remove_code_fences(source)

    assert not result.startswith("```")
    assert not result.endswith("```")
    assert "class TestCapability" in result