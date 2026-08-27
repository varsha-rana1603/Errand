from errand.core.plan import ExecutionPlan, PlanStep


def test_plan_step():

    step = PlanStep(
        capability="open_app",
        inputs={
            "app_name": "Safari",
        },
    )

    assert step.capability == "open_app"
    assert step.inputs["app_name"] == "Safari"


def test_execution_plan_can_contain_steps():

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                capability="open_app",
                inputs={
                    "app_name": "Safari",
                },
            ),
            PlanStep(
                capability="open_url",
                inputs={
                    "url": "https://youtube.com",
                },
            ),
        ]
    )

    assert len(plan.steps) == 2

    assert plan.steps[0].capability == "open_app"
    assert plan.steps[1].capability == "open_url"