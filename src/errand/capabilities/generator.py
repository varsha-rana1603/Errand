import json
from dataclasses import dataclass
import os

from openai import OpenAI


# ============================================================
# INPUT SCHEMA NORMALIZATION
# ============================================================

INPUT_TYPE_ALIASES = {
    "string": "string",
    str: "string",

    "integer": "integer",
    int: "integer",

    "float": "float",
    float: "float",

    "boolean": "boolean",
    bool: "boolean",
}


def normalize_input_schema(
    inputs: dict,
) -> dict[str, str]:
    """
    Convert all supported input type representations into
    Errand's canonical string representation.

    Examples:

        {"url": "string"}
            -> {"url": "string"}

        {"url": str}
            -> {"url": "string"}

        {"count": int}
            -> {"count": "integer"}

        {"enabled": bool}
            -> {"enabled": "boolean"}
    """

    if not isinstance(inputs, dict):
        raise ValueError(
            "Capability input_schema must be a dictionary."
        )

    normalized = {}

    for input_name, input_type in inputs.items():

        if not isinstance(input_name, str):
            raise ValueError(
                "Capability input names must be strings."
            )

        if input_type not in INPUT_TYPE_ALIASES:
            raise ValueError(
                f"Unsupported input type {input_type!r} "
                f"for input '{input_name}'."
            )

        normalized[input_name] = INPUT_TYPE_ALIASES[input_type]

    return normalized


@dataclass(frozen=True)
class GeneratedCapabilitySpec:
    """
    Specification for a capability that Errand wants to create.

    Input types are ALWAYS normalized into canonical strings:

        string
        integer
        float
        boolean
    """

    name: str
    description: str
    inputs: dict[str, str]

    def __post_init__(self):
        normalized_inputs = normalize_input_schema(
            self.inputs
        )

        object.__setattr__(
            self,
            "inputs",
            normalized_inputs,
        )


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
    Uses NVIDIA NIM to design and generate Errand capabilities.

    NVIDIA NIM exposes an OpenAI-compatible API, so we use the
    OpenAI Python client with NVIDIA's base URL.

    This class does NOT:
    - execute generated code
    - register capabilities
    - persist capabilities
    """

    def __init__(
        self,
        model: str = "openai/gpt-oss-20b",
    ):
        self.model = model

        print(
            f"[GENERATOR] Initializing NVIDIA NIM client "
            f"with model='{self.model}'"
        )

        api_key = os.environ.get("NVIDIA_API_KEY")

        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY environment variable is not set."
            )

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )

        print("[GENERATOR] NVIDIA NIM client initialized")

    # ============================================================
    # SPECIFICATION GENERATION
    # ============================================================

    def generate(
        self,
        name: str,
        description: str,
    ) -> GeneratedCapabilitySpec:

        print()
        print("=" * 70)
        print("[GENERATOR] STEP 1: GENERATING CAPABILITY SPECIFICATION")
        print("=" * 70)

        print(f"[GENERATOR] Requested name: {name!r}")
        print(
            f"[GENERATOR] Requested description: "
            f"{description!r}"
        )

        prompt = self._build_spec_prompt(
            name=name,
            description=description,
        )

        print("[GENERATOR] Sending specification prompt to NVIDIA...")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0,
                max_tokens=2000,
                reasoning_effort="low",
            )

        except Exception as exc:
            print(
                "[GENERATOR] NVIDIA specification request FAILED"
            )
            print(
                f"[GENERATOR] Exception: {type(exc).__name__}: {exc}"
            )
            raise

        print(
            "[GENERATOR] NVIDIA specification response received"
        )

        message = response.choices[0].message

        print(
            f"[GENERATOR] Finish reason: "
            f"{response.choices[0].finish_reason}"
        )

        print(
            f"[GENERATOR] Raw specification response:\n"
            f"{message.content}"
        )

        if not message.content:
            raise ValueError(
                "NVIDIA returned an empty capability specification."
            )

        print("[GENERATOR] Parsing capability specification...")

        spec = self._parse_spec(message.content)

        print("[GENERATOR] Parsed specification:")
        print(f"    name        = {spec.name!r}")
        print(
            f"    description = {spec.description!r}"
        )
        print(
            f"    inputs      = {spec.inputs!r}"
        )
        print(
            f"    input types = "
            f"{[(k, type(v).__name__) for k, v in spec.inputs.items()]}"
        )

        print(
            "[GENERATOR] Specification generation SUCCESS"
        )

        return spec

    # ============================================================
    # CODE GENERATION
    # ============================================================

    def generate_code(
        self,
        spec: GeneratedCapabilitySpec,
    ) -> GeneratedCapability:

        print()
        print("=" * 70)
        print("[GENERATOR] STEP 2: GENERATING CAPABILITY CODE")
        print("=" * 70)

        print("[GENERATOR] Specification received:")
        print(f"    name        = {spec.name!r}")
        print(
            f"    description = {spec.description!r}"
        )
        print(
            f"    inputs      = {spec.inputs!r}"
        )
        print(
            f"    input types = "
            f"{[(k, type(v).__name__) for k, v in spec.inputs.items()]}"
        )

        # --------------------------------------------------------
        # NORMALIZE INPUT SCHEMA BEFORE SENDING TO LLM
        # --------------------------------------------------------

        normalized_inputs = normalize_input_schema(
            spec.inputs
        )

        print(
            "[GENERATOR] Normalized input schema:"
        )
        print(
            f"    {normalized_inputs!r}"
        )

        inputs_json = json.dumps(
            normalized_inputs,
            indent=2,
        )

        print(
            "[GENERATOR] JSON representation of inputs:"
        )
        print(inputs_json)

        prompt = f"""
You are generating Python source code for a capability
inside Errand, a macOS AI assistant.

The capability specification below is AUTHORITATIVE.

NAME:
{spec.name}

DESCRIPTION:
{spec.description}

INPUTS:
{inputs_json}

Generate ONE complete Python source file.

REQUIRED STRUCTURE:

1. Import:

from errand.capabilities.base import Capability

2. Define exactly ONE subclass of Capability.

3. Implement these four members:

- name
- description
- input_schema
- execute(self, inputs)

CRITICAL CLASS INTERFACE:

`name` MUST be an @property.

`description` MUST be an @property.

`input_schema` MUST be an @property.

The class MUST follow this exact structure:

class ExampleCapability(Capability):

    @property
    def name(self) -> str:
        return "example"

    @property
    def description(self) -> str:
        return "Example capability."

    @property
    def input_schema(self) -> dict[str, str]:
        return {{
            "value": "string"
        }}

    def execute(self, inputs: dict):
        value = inputs["value"]
        ...

CRITICAL INPUT_SCHEMA RULE:

The input_schema property MUST return exactly:

{inputs_json}

The values MUST be STRING VALUES.

For example:

{{
    "url": "string"
}}

MUST generate:

@property
def input_schema(self):
    return {{
        "url": "string"
    }}

DO NOT generate:

@property
def input_schema(self):
    return {{
        "url": str
    }}

DO NOT use Python type objects such as:

- str
- int
- float
- bool

The canonical Errand input type strings are:

- "string"
- "integer"
- "float"
- "boolean"

They MUST remain strings inside input_schema.

EXECUTE METHOD:

The method MUST have exactly this form:

def execute(self, inputs):

`inputs` is ALWAYS a dictionary.

You MUST extract values from it using the exact input names.

For example:

def execute(self, inputs):
    url = inputs["url"]

Then operate on `url`.

NEVER treat `inputs` itself as the input value.

Do not rename input keys.
Do not add input keys.
Do not remove input keys.
Do not change input types.

SECURITY RULES:

- Do not use eval().
- Do not use exec().
- Do not use compile().
- Do not use __import__().
- Do not use ctypes.
- Do not use pickle.
- Do not use marshal.
- Do not use importlib.
- Do not access __globals__.
- Do not access __builtins__.
- Do not access __code__.
- Do not access __subclasses__.
- Do not access __bases__.
- Do not access __mro__.
- Do not download remote code.
- Do not execute remote code.
- Do not include secrets.
- Do not include credentials.
- Do not include API keys.
- Do not modify Errand source code.
- Do not modify the capability registry.
- Do not install packages.
- Do not include tests.

OUTPUT RULES:

- Return Python source code only.
- Do not use Markdown fences.
- Do not explain the code.
- Define exactly one Capability subclass.
"""

        print(
            "[GENERATOR] Sending code-generation prompt to NVIDIA..."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0,
                max_tokens=5000,
                reasoning_effort="low",
            )

        except Exception as exc:
            print(
                "[GENERATOR] NVIDIA code-generation request FAILED"
            )
            print(
                f"[GENERATOR] Exception: {type(exc).__name__}: {exc}"
            )
            raise

        print(
            "[GENERATOR] NVIDIA code-generation response received"
        )

        message = response.choices[0].message

        print(
            f"[GENERATOR] Finish reason: "
            f"{response.choices[0].finish_reason}"
        )

        print()
        print("[GENERATOR] RAW GENERATED RESPONSE:")
        print("-" * 70)
        print(message.content)
        print("-" * 70)

        if not message.content:
            raise ValueError(
                "NVIDIA generated empty capability source."
            )

        print(
            "[GENERATOR] Cleaning generated source..."
        )

        source = self._clean_source(message.content)

        print(
            f"[GENERATOR] Source length after cleaning: "
            f"{len(source)}"
        )

        print()
        print("[GENERATOR] CLEANED SOURCE:")
        print("-" * 70)
        print(source)
        print("-" * 70)

        if not source:
            raise ValueError(
                "NVIDIA generated empty capability source."
            )

        generated = GeneratedCapability(
            spec=spec,
            source=source,
        )

        print(
            "[GENERATOR] Returning GeneratedCapability"
        )

        print(
            "[GENERATOR] Expected specification:"
        )
        print(f"    {generated.spec}")

        print(
            "[GENERATOR] Expected input_schema:"
        )
        print(f"    {generated.spec.inputs}")

        return generated

    # ============================================================
    # FULL GENERATION
    # ============================================================

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

    # ============================================================
    # SPECIFICATION PROMPT
    # ============================================================

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

Create a precise specification.

Return exactly one JSON object containing:

- name
- description
- inputs

The inputs object maps input names to one of:

- string
- integer
- float
- boolean

Example:

{{
    "name": "open_url",
    "description": "Open a URL in the user's web browser.",
    "inputs": {{
        "url": "string"
    }}
}}

Rules:

- Return valid JSON only.
- Do not generate Python.
- Do not generate shell commands.
- Do not execute anything.
- Do not include Markdown.
"""

    # ============================================================
    # SPECIFICATION PARSER
    # ============================================================

    @staticmethod
    def _parse_spec(
        text: str,
    ) -> GeneratedCapabilitySpec:

        try:
            data = json.loads(text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "NVIDIA returned invalid capability specification: "
                f"{exc}"
            ) from exc

        name = data.get("name")
        description = data.get("description")
        inputs = data.get("inputs")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Generated capability is missing a valid name."
            )

        if (
            not isinstance(description, str)
            or not description.strip()
        ):
            raise ValueError(
                "Generated capability is missing a valid description."
            )

        if not isinstance(inputs, dict):
            raise ValueError(
                "Generated capability inputs must be an object."
            )

        # --------------------------------------------------------
        # NORMALIZE INPUT SCHEMA
        # --------------------------------------------------------

        try:
            normalized_inputs = normalize_input_schema(
                inputs
            )

        except ValueError as exc:
            raise ValueError(
                f"Invalid capability input schema: {exc}"
            ) from exc

        print(
            "[GENERATOR] Input schema normalized:"
        )
        print(
            f"    original  = {inputs!r}"
        )
        print(
            f"    normalized = {normalized_inputs!r}"
        )

        return GeneratedCapabilitySpec(
            name=name.strip(),
            description=description.strip(),
            inputs=normalized_inputs,
        )

    # ============================================================
    # SOURCE CLEANER
    # ============================================================

    @staticmethod
    def _clean_source(
        text: str,
    ) -> str:

        source = text.strip()

        if source.startswith("```python"):
            source = source[len("```python"):].strip()

        elif source.startswith("```"):
            source = source[len("```"):].strip()

        if source.endswith("```"):
            source = source[:-3].strip()

        return source