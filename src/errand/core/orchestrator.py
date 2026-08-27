from dataclasses import dataclass
from errand.core.intent import Intent
from errand.skills.base import Skill
from errand.skills.registry import SkillNotFoundError, SkillRegistry
from errand.core.interaction import InteractionType, UserInteraction

@dataclass
class Clarification:
    field: str
    question: str

@dataclass
class ExecutionResult:
    status: str
    message: str
    skill: Skill | None = None
    missing_fields: set[str] | None = None
    clarification: Clarification | None = None
    interaction: UserInteraction | None = None

class Orchestrator:
    #Controls the flow from Intent to Skill execution
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def prepare(self, intent: Intent) -> ExecutionResult:
        #Resolve an Intent and determine what needs to happen next

        try:
            skill = self.registry.resolve(intent)
        except SkillNotFoundError as error:
            return ExecutionResult(status = "unsupported", message = str(error))

        missing_fields = {
            field
            for field in skill.required_fields
            if field not in intent.fields
            or intent.fields[field] is None
        }

        if missing_fields:
            field = next(iter(missing_fields))

            question = skill.field_questions.get(field)

            if question is None:
                question = f"Please provide '{field}'."

            return ExecutionResult(
                status="needs_input",
                message = question,
                skill = skill,
                missing_fields = missing_fields,
                clarification = Clarification(
                    field = field,
                    question = question
                ),
                interaction = UserInteraction(
                    type = InteractionType.INPUT,
                    prompt = question,
                    field = field
                )
            )

        return ExecutionResult(
            status = "ready",
            message = "Ready to execute",
            skill = skill
        )

    def confirm(self, skill: Skill) -> bool:
        """
        Ask the user for confirmation when required.

        Execution is never performed automatically by this method.
        """

        if not skill.requires_confirmation:
            return True

        answer = input("Proceed? [y/N] ").strip().lower()

        return answer in {"y", "yes"}

    def execute(
        self,
        intent: Intent,
        skill: Skill,
    ) -> ExecutionResult:
        """
        Execute a skill after all required checks have passed.
        """

        result = skill.execute(intent)

        return ExecutionResult(
            status="executed",
            message=str(result) if result is not None else "Done.",
            skill=skill,
        )