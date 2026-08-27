import subprocess
from errand.core.intent import Intent
from errand.skills.base import Skill

class OpenAppSkill(Skill):
    #Opens a macOS application by name

    @property
    def action(self) -> str:
        return "open_app"

    @property
    def required_fields(self) -> set[str]:
        return {"app_name"}

    @property
    def field_questions(self) -> dict[str, str]:
        return {
            "app_name": "Which application would you like me to open?"
        }

    @property
    def input_questions(self):
        return {
            "app_name": "Which application would you like me to open?"
        }

    def execute(self, intent: Intent) -> str:
        app_name = intent.fields["app_name"]

        subprocess.run(
            ["open", "-a", app_name],
            check=True,
        )

        return f"Opened {app_name}."
