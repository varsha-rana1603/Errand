import json

from errand.capabilities.generator import (
    CapabilityGenerator,
    GeneratedCapability,
    GeneratedCapabilitySpec,
)


class FakeResponse:

    def __init__(self, text):
        self.text = text


class FakeClient:

    class Models:

        def __init__(self, response):
            self.response = response
            self.calls = []

        def generate_content(self, model, contents):
            self.calls.append(
                {
                    "model": model,
                    "contents": contents,
                }
            )

            return self.response

    def __init__(self, response):
        self.models = self.Models(response)


def test_generator_creates_capability_spec():

    response = FakeResponse(
        json.dumps(
            {
                "name": "play_music",
                "description": (
                    "Play a requested song using a music service."
                ),
                "inputs": {
                    "song": "string",
                    "artist": "string",
                    "service": "string",
                },
            }
        )
    )

    generator = CapabilityGenerator()

    generator.client = FakeClient(response)

    result = generator.generate(
        name="play_music",
        description=(
            "Play a requested song using a music service."
        ),
    )

    assert isinstance(result, GeneratedCapabilitySpec)

    assert result.name == "play_music"

    assert result.description == (
        "Play a requested song using a music service."
    )

    assert result.inputs == {
        "song": "string",
        "artist": "string",
        "service": "string",
    }


def test_generator_rejects_invalid_json():

    generator = CapabilityGenerator()

    generator.client = FakeClient(
        FakeResponse("this is not json")
    )

    try:
        generator.generate(
            name="play_music",
            description="Play music.",
        )

        assert False, "Expected ValueError"

    except ValueError as exc:

        assert "invalid capability specification" in str(exc)


def test_generator_rejects_missing_name():

    generator = CapabilityGenerator()

    generator.client = FakeClient(
        FakeResponse(
            json.dumps(
                {
                    "description": "Play music.",
                    "inputs": {},
                }
            )
        )
    )

    try:
        generator.generate(
            name="play_music",
            description="Play music.",
        )

        assert False, "Expected ValueError"

    except ValueError as exc:

        assert "missing a valid name" in str(exc)


def test_generator_rejects_invalid_input_type():

    generator = CapabilityGenerator()

    generator.client = FakeClient(
        FakeResponse(
            json.dumps(
                {
                    "name": "play_music",
                    "description": "Play music.",
                    "inputs": {
                        "song": "banana",
                    },
                }
            )
        )
    )

    try:
        generator.generate(
            name="play_music",
            description="Play music.",
        )

        assert False, "Expected ValueError"

    except ValueError as exc:

        assert "Unsupported input type" in str(exc)


def test_generator_creates_capability_source():

    response = FakeResponse(
        """
from errand.capabilities.base import Capability


class PlayMusicCapability(Capability):

    @property
    def name(self):
        return "play_music"

    @property
    def description(self):
        return "Play a requested song."

    @property
    def input_schema(self):
        return {
            "song": str,
            "artist": str,
            "service": str,
        }

    def execute(self, inputs):
        return "Music played."
"""
    )

    generator = CapabilityGenerator()

    generator.client = FakeClient(response)

    spec = GeneratedCapabilitySpec(
        name="play_music",
        description="Play a requested song.",
        inputs={
            "song": "string",
            "artist": "string",
            "service": "string",
        },
    )

    result = generator.generate_code(spec)

    assert isinstance(result, GeneratedCapability)

    assert result.spec == spec

    assert "class PlayMusicCapability" in result.source

    assert "def execute" in result.source

    assert "play_music" in result.source


def test_generator_removes_python_markdown_fences():

    response = FakeResponse(
        """
```python
from errand.capabilities.base import Capability


class ExampleCapability(Capability):

    @property
    def name(self):
        return "example"

    def execute(self, inputs):
        return "done"
````

"""
)

    generator = CapabilityGenerator()

    generator.client = FakeClient(response)

    spec = GeneratedCapabilitySpec(
        name="example",
        description="Example capability.",
        inputs={},
    )

    result = generator.generate_code(spec)

    assert "```python" not in result.source

    assert "```" not in result.source

    assert result.source.startswith(
        "from errand.capabilities.base import Capability"
    )

def test_generator_rejects_empty_generated_source():

    generator = CapabilityGenerator()

    generator.client = FakeClient(
        FakeResponse("   ")
    )

    spec = GeneratedCapabilitySpec(
        name="example",
        description="Example capability.",
        inputs={},
    )

    try:
        generator.generate_code(spec)

        assert False, "Expected ValueError"

    except ValueError as exc:

        assert "empty capability source" in str(exc)

def test_generator_generate_full():
    spec_response = FakeResponse(
        json.dumps(
            {
                "name": "play_music",
                "description": (
                    "Play a requested song using a music service."
                ),
                "inputs": {
                    "song": "string",
                    "artist": "string",
                    "service": "string",
                },
            }
        )
    )

    code_response = FakeResponse(
        """
    ```

    from errand.capabilities.base import Capability

    class PlayMusicCapability(Capability):

    ```
    @property
    def name(self):
        return "play_music"

    @property
    def description(self):
        return "Play music."

    @property
    def input_schema(self):
        return {
            "song": str,
            "artist": str,
            "service": str,
        }

    def execute(self, inputs):
        return "Music played."
    ```

    """
    )

    generator = CapabilityGenerator()

    class SequentialClient:

        class Models:

            def __init__(self):
                self.responses = iter(
                    [
                        spec_response,
                        code_response,
                    ]
                )

            def generate_content(self, model, contents):
                return next(self.responses)

        def __init__(self):
            self.models = self.Models()

    generator.client = SequentialClient()

    result = generator.generate_full(
        name="play_music",
        description=(
            "Play a requested song using a music service."
        ),
    )

    assert isinstance(result, GeneratedCapability)

    assert result.spec.name == "play_music"

    assert result.spec.inputs == {
        "song": "string",
        "artist": "string",
        "service": "string",
    }

    assert "class PlayMusicCapability" in result.source

    assert "def execute" in result.source
