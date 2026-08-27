from errand.agent.decision import AgentDecision


def test_capability_decision():

    decision = AgentDecision(
        type="capability",
        capability="search_web",
        inputs={
            "query": "liver cancer articles",
        },
    )

    assert decision.type == "capability"
    assert decision.capability == "search_web"
    assert decision.inputs["query"] == "liver cancer articles"


def test_ask_user_decision():

    decision = AgentDecision(
        type="ask_user",
        question="Which platform would you like me to use?",
    )

    assert decision.type == "ask_user"
    assert decision.question == "Which platform would you like me to use?"


def test_finish_decision():

    decision = AgentDecision(
        type="finish",
        result="Task completed.",
    )

    assert decision.type == "finish"
    assert decision.result == "Task completed."


def test_fail_decision():

    decision = AgentDecision(
        type="fail",
        reason="Capability unavailable.",
    )

    assert decision.type == "fail"
    assert decision.reason == "Capability unavailable."