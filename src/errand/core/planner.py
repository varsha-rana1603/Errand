from errand.core.intent import Intent
from errand.core.plan import ExecutionPlan , PlanStep
from errand.skills.registry import SkillRegistry, SkillNotFoundError

class Planner:
    #Converts Intent into an ExecutionPlan

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def plan(self, intent: Intent) -> ExecutionPlan:
        #Create an execution plan for an Intent
        skill = self.registry.resolve(intent)

        step = PlanStep(capability = skill.action, inputs = dict(intent.fields))

        return ExecutionPlan(
            steps = [step]
        )