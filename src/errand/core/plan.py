from dataclasses import dataclass, field

@dataclass
class PlanStep:
    #One capability invocation in an execution plan
    capability: str
    inputs: dict = field(default_factory = dict)

@dataclass
class ExecutionPlan:
    #A sequence of capability invocoations that Errand should execute
    steps: list[PlanStep] = field(default_factory = list)

    