from errand.agent.context import AgentContext
from errand.agent.decision import AgentDecision


def test_context_stores_goal():

    context = AgentContext(
        goal="Find the top five articles on liver cancer"
    )

    assert context.goal == "Find the top five articles on liver cancer"
    assert context.history == []


def test_context_stores_user_message():

    context = AgentContext(
        goal="Find articles"
    )

    context.add_user_message("Use recent articles.")

    assert context.history[-1] == {
        "role": "user",
        "content": "Use recent articles.",
    }


def test_context_stores_agent_decision():

    context = AgentContext(
        goal="Find articles"
    )

    decision = AgentDecision(
        type="capability",
        capability="search_web",
        inputs={
            "query": "liver cancer"
        },
    )

    context.add_agent_decision(decision)

    assert context.history[-1]["role"] == "agent"
    assert context.history[-1]["decision"] is decision


def test_context_stores_observation():

    context = AgentContext(
        goal="Find articles"
    )

    context.add_observation(
        ["Article A", "Article B"]
    )

    assert context.last_observation() == [
        "Article A",
        "Article B",
    ]


def test_last_observation_returns_latest():

    context = AgentContext(
        goal="Find articles"
    )

    context.add_observation("first")
    context.add_observation("second")

    assert context.last_observation() == "second"


def test_last_observation_returns_none_when_empty():

    context = AgentContext(
        goal="Find articles"
    )

    assert context.last_observation() is None