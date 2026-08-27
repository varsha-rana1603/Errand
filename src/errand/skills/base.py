from abc import ABC, abstractmethod
from errand.core.intent import Intent

class Skill(ABC):
    #Base class for all Errand skills.
    #A skill represents one capability that Errand can perform.

    @property
    @abstractmethod
    def action(self) -> str:
        #The action name this skill handles
        raise NotImplementedError

    @property
    def required_fields(self) -> set[str]:
        #Fields that must be present before execution
        #Skills can override this when they need specific gields
        return set()

    @property
    def requires_confirmation(self) -> bool:
        #Whether the skill requires explicit user confirmation before execution
        #Irreversible actions should return True

        return False

    @property
    def field_questions(self) -> dict[str, str]:
        """
        Questions to ask when required fields are missing.

        Keys are field names.
        Values are user-facing clarification questions.
        """
        return {}

    @property
    def input_questions(self) -> dict[str, str]:
        #Human-friendly questions for required inputs
        return {}
    

    def can_handle(self, intent: Intent) -> bool:
        #Determine whether this skill can handle an Intent
        if intent.action != self.action:
            return False

        return all(
            field in intent.fields
            and intent.fields[field] is not None
            for field in self.required_fields
        )

    @abstractmethod
    def execute(self, intent: Intent):
        #Execute the skill
        raise NotImplementedError 