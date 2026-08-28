import json
from dataclasses import dataclass

from google import genai

from errand.capabilities.generator import GeneratedCapabilitySpec


@dataclass(frozen=True)
class GeneratedCapabilityCode:
    """
    Executable Python source generated for a capability.

    This is source code only. It must be validated and sandbox-tested
    before it is ever loaded or executed.
    """

    name: str
    source: str


class CapabilityCodeGenerator:
    """
    Generates Python implementation code for an approved capability.

    This class does NOT execute the generated code.
    """

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
    ):
        self.model = model
        self.client = genai.Client()

    def generate(
        self,
        spec: GeneratedCapabilitySpec,
    ) -> GeneratedCapabilityCode:

        prompt = f"""
You are generating a Python capability for Errand,
a general-purpose macOS AI assistant.

The capability has already been specified and approved by the user.

CAPABILITY NAME:
{spec.name}

CAPABILITY DESCRIPTION:
{spec.description}

CAPABILITY INPUTS:
{json.dumps(spec.inputs, indent=2)}

Generate a complete Python implementation.

The implementation MUST:

- Import Capability from errand.capabilities.base.
- Define exactly one Capability subclass.
- Implement the name property.
- Implement the description property.
- Implement the input_schema property.
- Implement the execute(inputs) method.
- Use the exact capability name: {spec.name}.
- Use only the inputs defined in the specification.
- Return a useful result from execute().
- Use standard Python libraries whenever possible.
- Interact with macOS only through explicit, understandable operations.
- Never execute arbitrary code supplied through user input.
- Never use eval().
- Never use exec().
- Never download and execute remote code.
- Never modify Errand's own source code.
- Never modify the capability registry directly.
- Never install Python packages.
- Do not include tests.
- Do not include Markdown fences.
- Return ONLY valid Python source code.

The generated class must follow this general structure:

from errand.capabilities.base import Capability


class SomeCapability(Capability):

    @property
    def name(self) -> str:
        return "capability_name"

    @property
    def description(self) -> str:
        return "description"

    @property
    def input_schema(self) -> dict[str, type]:
        return {{
            "input_name": str,
        }}

    def execute(self, inputs: dict) -> object:
        ...
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        source = response.text.strip()

        if source.startswith("```"):
            source = self._remove_code_fences(source)

        if not source:
            raise ValueError(
                "Gemini returned empty capability code."
            )

        return GeneratedCapabilityCode(
            name=spec.name,
            source=source,
        )

    @staticmethod
    def _remove_code_fences(source: str) -> str:

        lines = source.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines).strip()