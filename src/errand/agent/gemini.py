import json

from google import genai
from google.genai import errors

from errand.agent.context import AgentContext
from errand.agent.decision import AgentDecision
from errand.capabilities.registry import CapabilityRegistry


class GeminiAgentModel:
    """
    Gemini-backed implementation of AgentModel.

    Gemini decides what Errand should do next.
    It does not directly execute capabilities.

    If a required capability does not exist, Gemini can request
    that Errand generate a new capability.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        model: str = "gemini-3.6-flash",
    ):
        self.registry = registry
        self.model = model
        self.client = genai.Client()

    def decide(
        self,
        context: AgentContext,
    ) -> AgentDecision:

        prompt = self._build_prompt(context)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )

        except errors.APIError as exc:

            # ----------------------------------------------
            # RATE LIMIT / QUOTA
            # ----------------------------------------------

            if exc.code == 429:

                return AgentDecision(
                    type="fail",
                    reason=(
                        "Gemini API quota has been exceeded. "
                        "Please wait and try again later, or "
                        "check your Gemini API plan and billing "
                        "limits."
                    ),
                )

            # ----------------------------------------------
            # AUTHENTICATION
            # ----------------------------------------------

            if exc.code == 401:

                return AgentDecision(
                    type="fail",
                    reason=(
                        "Gemini authentication failed. "
                        "Please check your Gemini API key."
                    ),
                )

            # ----------------------------------------------
            # PERMISSION
            # ----------------------------------------------

            if exc.code == 403:

                return AgentDecision(
                    type="fail",
                    reason=(
                        "Gemini denied the request. "
                        "Please check your API key, project "
                        "permissions, and billing configuration."
                    ),
                )

            # ----------------------------------------------
            # MODEL NOT FOUND
            # ----------------------------------------------

            if exc.code == 404:

                return AgentDecision(
                    type="fail",
                    reason=(
                        f"Gemini model '{self.model}' was not "
                        "found or is not available to this API key."
                    ),
                )

            # ----------------------------------------------
            # OTHER GEMINI API ERROR
            # ----------------------------------------------

            return AgentDecision(
                type="fail",
                reason=(
                    "Gemini API request failed"
                    f" ({exc.code}): {exc.message}"
                ),
            )

        except Exception as exc:

            # ----------------------------------------------
            # UNEXPECTED ERROR
            # ----------------------------------------------

            return AgentDecision(
                type="fail",
                reason=(
                    "Unexpected error while contacting Gemini: "
                    f"{exc}"
                ),
            )

        # ----------------------------------------------
        # PARSE MODEL RESPONSE
        # ----------------------------------------------

        if not response.text:

            return AgentDecision(
                type="fail",
                reason=(
                    "Gemini returned an empty response."
                ),
            )

        return self._parse_response(
            response.text
        )

    def _build_prompt(
        self,
        context: AgentContext,
    ) -> str:

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

Errand is an ACTION-ORIENTED assistant.

IMPORTANT DISTINCTION:

If the user's request can be answered purely with information
or reasoning, you may return "finish".

If the user's request requires PERFORMING an ACTION outside
the model itself, you MUST use a capability.

For an action:

1. If a suitable capability exists in the capability manifest,
use "capability".

2. If no suitable capability exists, use
"generate_capability".

3. Do NOT simply return "finish" with a description of what
could be done.

Examples of ACTIONS that require capabilities:

- Opening an application
- Closing an application
- Playing music
- Sending a message
- Creating a file
- Deleting a file
- Moving or renaming a file
- Searching the filesystem
- Opening a URL
- Controlling a macOS application
- Interacting with an external service
- Performing an operation on behalf of the user

Examples of INFORMATION requests that may use "finish":

- "What is the capital of France?"
- "Explain recursion."
- "What does this Python code do?"
- "Translate this sentence."
- "What is 25 * 4?"

The capability system is the mechanism through which Errand
performs actions.

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

Use this ONLY when the requested action can be performed
by a capability that exists in the capability manifest.

Never invent a capability.

2. generate_capability

{{
    "type": "generate_capability",
    "capability": "capability_name",
    "capability_description": "Detailed description of what the capability should do"
}}

Use this when:

- The user's request requires performing an action,
- AND no suitable capability exists in the manifest.

The capability description should clearly explain:

- What the capability does
- What inputs it needs
- What external application, operating-system facility,
API, or service it interacts with
- What successful execution should accomplish

Do NOT include Python code.

3. ask_user

{{
    "type": "ask_user",
    "question": "Question to ask the user"
}}

Use this when information required to perform the requested
action is missing or ambiguous.

4. finish

{{
    "type": "finish",
    "result": "Final response to the user"
}}

Use this when:

- The user's request is informational, OR
- The requested action has already been successfully completed.

IMPORTANT:

Do NOT use "finish" merely because you know how an action
could be performed.

If the user asks Errand to perform an action, Errand must
actually perform it through a capability.

5. fail

{{
    "type": "fail",
    "reason": "Why the task cannot be completed"
}}

Use this only when the task cannot reasonably be completed.

RULES:

- Never invent an existing capability.
- Never use a capability that is not in the manifest.
- If an ACTION requires a capability that does not exist,
use generate_capability.
- Never claim that an action was performed unless a
capability actually performed it.
- Never execute or claim to execute generated capability code.
- Capability generation is only a request to another
Errand component.
- Never invent capability inputs for an existing capability.
- If required information is missing, ask the user.
- Perform only one capability invocation per decision.
- After observing a capability result, decide what to do next.
- Do not return Markdown.
- Return valid JSON only.
"""

    @staticmethod
    def _parse_response(
        text: str,
    ) -> AgentDecision:

        try:

            data = json.loads(text)

        except json.JSONDecodeError as exc:

            return AgentDecision(
                type="fail",
                reason=(
                    f"Gemini returned invalid JSON: {exc}"
                ),
            )

        return AgentDecision(
            type=data.get("type"),
            capability=data.get("capability"),
            capability_description=data.get(
                "capability_description"
            ),
            inputs=data.get(
                "inputs",
                {},
            ),
            question=data.get(
                "question"
            ),
            result=data.get(
                "result"
            ),
            reason=data.get(
                "reason"
            ),
        )

