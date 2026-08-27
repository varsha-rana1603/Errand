from errand.core.intent import Intent
from errand.parser.base import Parser

class MockParser(Parser):

    def parse(self, text: str) -> Intent:
        return Intent(
            action = "mock_action",
            fields = {
                "original_text": text
            }
        )