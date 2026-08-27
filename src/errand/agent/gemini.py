import json

from google import genai

from errand.agent.context import AgentContext
from errand.agent.decision import AgentDecision
from errand.capabilities.registry import CapabilityRegistry


class GeminiAgentModel:
    """
    Gemini-backed implementation of AgentModel.

    Gemini decides what Errand should do next.
    It does not directly execute capabilities.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        model: str = "gemini-3.6-flash",
    ):
        self.registry = registry
        self.model = model

        self.client = genai.Client()

    def decide(self, context: AgentContext) -> AgentDecision:

        prompt = self._build_prompt(context)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return self._parse_response(response.text)

    def _build_prompt(self, context: AgentContext) -> str:

        manifest = self.registry.manifest()

        history = json.dumps(
            context.history,
            default=str,
            indent=2,
        )

        return f"""
You are the decision-making agent inside Errand,
a general-purpose macOS assistant.

Your job is to decide the NEXT action required to accomplish
the user's goal.

You do NOT execute actions yourself.

You may only request capabilities that appear in the
capability manifest below.

CAPABILITY MANIFEST:

{json.dumps(manifest, indent=2)}

USER GOAL:

{context.goal}

TASK HISTORY:

{history}

Return EXACTLY one JSON object.

Allowed decision types:

1. capability

{{
    "type": "capability",
    "capability": "capability_name",
    "inputs": {{
        "input_name": "value"
    }}
}}

2. ask_user

{{
    "type": "ask_user",
    "question": "Question to ask the user"
}}

3. finish

{{
    "type": "finish",
    "result": "Final response to the user"
}}

4. fail

{{
    "type": "fail",
    "reason": "Why the task cannot be completed"
}}

Rules:

- Never invent capabilities.
- Never invent capability inputs.
- If required information is missing, ask the user.
- If the task requires a capability that does not exist,
  fail rather than pretending it exists.
- Perform only one capability invocation per decision.
- After observing a capability result, decide what to do next.
- Do not return Markdown.
- Return valid JSON only.
"""

    @staticmethod
    def _parse_response(text: str) -> AgentDecision:

        try:
            data = json.loads(text)

        except json.JSONDecodeError as exc:

            return AgentDecision(
                type="fail",
                reason=f"Gemini returned invalid JSON: {exc}",
            )

        return AgentDecision(
            type=data.get("type"),
            capability=data.get("capability"),
            inputs=data.get("inputs", {}),
            question=data.get("question"),
            result=data.get("result"),
            reason=data.get("reason"),
        )