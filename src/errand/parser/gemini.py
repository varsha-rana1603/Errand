import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from errand.core.intent import Intent
from errand.parser.base import Parser
from errand.parser.schema import ParsedIntent


load_dotenv()


def parsed_intent_to_intent(parsed: ParsedIntent) -> Intent:
    """
    Convert Gemini's structured response into Errand's internal Intent.

    This function contains no API calls and no external dependencies,
    so it can be tested independently.
    """

    fields = {
        field.name: field.value
        for field in parsed.fields
    }

    return Intent(
        action=parsed.action,
        fields=fields,
    )


class GeminiParser(Parser):

    def __init__(self, model: str = "gemini-3.6-flash"):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def parse(self, text: str) -> Intent:

        response = self.client.models.generate_content(
            model=self.model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are the intent parser for Errand, "
                    "an open-source natural-language command tool "
                    "for macOS.\n\n"

                    "Your ONLY job is to understand what the user "
                    "wants and represent that as a structured intent.\n\n"

                    "Do NOT execute any action.\n"
                    "Do NOT provide shell commands.\n"
                    "Do NOT provide AppleScript.\n"
                    "Do NOT invent missing information.\n\n"

                    "Extract information explicitly provided by the user. "
                    "If relevant information is missing, create the field "
                    "with a null value rather than guessing."
                ),
                response_mime_type="application/json",
                response_schema=ParsedIntent,
            ),
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        parsed = ParsedIntent.model_validate_json(response.text)

        return parsed_intent_to_intent(parsed)