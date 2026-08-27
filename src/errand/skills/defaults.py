from errand.skills.open_app import OpenAppSkill
from errand.skills.registry import SkillRegistry


def create_default_registry() -> SkillRegistry:
    registry = SkillRegistry()

    registry.register(OpenAppSkill())

    return registry