from errand.core.plan import ExecutionPlan
from errand.skills.registry import SkillRegistry

class SafetyGate:
    #Determines whether an execution plan is allowed to proceed

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def requires_confirmation(self, plan: ExecutionPlan) -> bool:
        #Return True if any step in the plan required confirmation
        for step in plan.steps:
            skill = self.registry.get(step.capability)

            if skill.requires_confirmation:
                return True

        return False

    def preview(self, plan: ExecutionPlan) -> str:
        #Create a human-readable preview of the execution plan
        lines = ["Errand wants to perform: "]

        for step in plan.steps:
            lines.append(f"- {step.capability}")

            for name, value in step.inputs.items():
                lines.append(f" {name}: {value}")

        return "\n".join(lines)

    def confirm(self, plan: ExecutionPlan) -> bool:
        #ASk the user for confirmation when required
        #Return True if execution is allowed

        if not self.requires_confirmation(plan):
            return True

        print()
        print(self.preview(plan))
        print()

        answer = input("Proceed with this action? [y/N] ")
        return answer.strip().lower() in {"y", "yes"}