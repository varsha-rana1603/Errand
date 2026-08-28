import json
from dataclasses import dataclass

from google import genai


@dataclass(frozen=True)
class GeneratedCapabilitySpec:
    """
    Specification for a capability that Errand wants to create.
    """

    name: str
    description: str
    inputs: dict[str, str]


@dataclass(frozen=True)
class GeneratedCapability:
    """
    A generated capability specification plus candidate Python source.

    The source is untrusted and MUST be validated and sandbox-tested
    before it can ever be registered or executed.
    """

    spec: GeneratedCapabilitySpec
    source: str


class CapabilityGenerator:
    """
    Uses Gemini to design and generate a new Errand capability.

    Generated source is treated as untrusted code.
    This class does NOT execute, register, or persist it.
    """

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
    ):
        self.model = model
        self.client = genai.Client()

    def generate(
        self,
        name: str,
        description: str,
    ) -> GeneratedCapabilitySpec:

        prompt = self._build_spec_prompt(
            name=name,
            description=description,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return self._parse_spec(response.text)

    def generate_code(
        self,
        spec: GeneratedCapabilitySpec,
    ) -> GeneratedCapability:

        prompt = f"""
You are generating Python source code for a capability
inside Errand, a macOS AI assistant.

The capability specification was already created.

NAME:
{spec.name}

DESCRIPTION:
{spec.description}

INPUTS:
{json.dumps(spec.inputs, indent=2)}

Generate ONE complete Python source file implementing this
capability.

The implementation must:

- import Capability from errand.capabilities.base
- define exactly one Capability subclass
- implement name
- implement description
- implement input_schema
- implement execute
- use the specified input names
- return a useful result from execute

IMPORTANT SECURITY RULES:

- Do not use eval().
- Do not use exec().
- Do not use compile().
- Do not use __import__().
- Do not use ctypes.
- Do not use pickle.
- Do not use marshal.
- Do not use importlib.
- Do not access __globals__, __builtins__, __code__,
  __subclasses__, __bases__, or __mro__.
- Do not download or execute remote code.
- Do not include secrets, credentials, API keys, or tokens.
- Do not modify Errand's source code.
- Do not modify the capability registry.
- Do not install packages.
- Do not include tests.
- Do not include Markdown fences.
- Return Python source code only.

The generated code will be statically checked and
executed inside a sandbox before it can become trusted.

The source will be treated as UNTRUSTED and will be
statically validated and sandbox-tested before it can
ever be registered or executed.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        source = self._clean_source(response.text)

        if not source:
            raise ValueError(
                "Gemini generated empty capability source."
            )

        return GeneratedCapability(
            spec=spec,
            source=source,
        )

    def generate_full(
        self,
        name: str,
        description: str,
    ) -> GeneratedCapability:

        spec = self.generate(
            name=name,
            description=description,
        )

        return self.generate_code(spec)

    def _build_spec_prompt(
        self,
        name: str,
        description: str,
    ) -> str:

        return f"""
You are designing a new capability for Errand,
a general-purpose macOS AI assistant.

The capability does not currently exist.

CAPABILITY NAME:

{name}

REQUESTED BEHAVIOR:

{description}

Create a precise specification for this capability.

The specification must contain:

- name
- description
- inputs

The inputs object must map each required input name
to a simple Python type name such as:

- string
- integer
- float
- boolean

Return EXACTLY one JSON object:

{{
    "name": "capability_name",
    "description": "What the capability does",
    "inputs": {{
        "input_name": "string"
    }}
}}

Rules:

- Do not generate Python code.
- Do not generate shell commands.
- Do not execute anything.
- Do not include Markdown.
- Return valid JSON only.
"""

    @staticmethod
    def _parse_spec(text: str) -> GeneratedCapabilitySpec:

        try:
            data = json.loads(text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Gemini returned invalid capability specification: "
                f"{exc}"
            ) from exc

        name = data.get("name")
        description = data.get("description")
        inputs = data.get("inputs")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Generated capability is missing a valid name."
            )

        if not isinstance(description, str) or not description.strip():
            raise ValueError(
                "Generated capability is missing a valid description."
            )

        if not isinstance(inputs, dict):
            raise ValueError(
                "Generated capability inputs must be an object."
            )

        allowed_types = {
            "string",
            "integer",
            "float",
            "boolean",
        }

        for input_name, input_type in inputs.items():

            if not isinstance(input_name, str):
                raise ValueError(
                    "Capability input names must be strings."
                )

            if input_type not in allowed_types:
                raise ValueError(
                    f"Unsupported input type '{input_type}' "
                    f"for input '{input_name}'."
                )

        return GeneratedCapabilitySpec(
            name=name.strip(),
            description=description.strip(),
            inputs=inputs,
        )

    @staticmethod
    def _clean_source(text: str) -> str:

        source = text.strip()

        if source.startswith("```python"):
            source = source[len("```python"):].strip()

        elif source.startswith("```"):
            source = source[len("```"):].strip()

        if source.endswith("```"):
            source = source[:-3].strip()

        return source