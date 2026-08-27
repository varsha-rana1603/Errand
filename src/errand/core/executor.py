from errand.core.plan import ExecutionPlan
from errand.skills.registry import SkillRegistry

class Executor:
    #Executes an ExecutionPlan using registered skills

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def execute(self, plan: ExecutionPlan): 
        #Execute every step in the plan in order
        #Result -> A list containing the result of each skill execution

        results = []
        for step in plan.steps:
            skill = self.registry.get(step.capability)

            from errand.core.intent import Intent

            intent = Intent(
                action = step.capability,
                fields = dict(step.inputs)
            )

            result = skill.execute(intent)

            results.append(result)

        return results

    