from errand.core.intent import Intent
from errand.skills.base import Skill


class SkillNotFoundError(Exception):
    """Raised when no registered skill can handle an Intent."""


class SkillRegistry:
    """
    Stores and resolves Errand skills.
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """
        Register a skill.
        """

        if skill.action in self._skills:
            raise ValueError(
                f"A skill for action '{skill.action}' "
                "is already registered."
            )

        self._skills[skill.action] = skill

    def get(self, action: str) -> Skill:
        """
        Retrieve a skill by action name.
        """

        try:
            return self._skills[action]
        except KeyError:
            raise SkillNotFoundError(
                f"No skill registered for action '{action}'."
            )

    def resolve(self, intent: Intent) -> Skill:
        """
        Resolve an Intent to the skill responsible for its action.

        Missing fields are NOT handled here.
        The Orchestrator is responsible for detecting
        missing information and asking the user for it.
        """

        return self.get(intent.action)

    def all(self) -> list[Skill]:
        """
        Return all registered skills.
        """

        return list(self._skills.values())