from errand.agent.gemini import GeminiAgentModel


def test_parse_capability_decision():

    response = """
    {
        "type": "capability",
        "capability": "open_app",
        "inputs": {
            "app_name": "Safari"
        }
    }
    """

    decision = GeminiAgentModel._parse_response(response)

    assert decision.type == "capability"
    assert decision.capability == "open_app"
    assert decision.inputs == {
        "app_name": "Safari"
    }


def test_parse_ask_user_decision():

    response = """
    {
        "type": "ask_user",
        "question": "Which platform should I use?"
    }
    """

    decision = GeminiAgentModel._parse_response(response)

    assert decision.type == "ask_user"
    assert decision.question == "Which platform should I use?"


def test_parse_finish_decision():

    response = """
    {
        "type": "finish",
        "result": "The task is complete."
    }
    """

    decision = GeminiAgentModel._parse_response(response)

    assert decision.type == "finish"
    assert decision.result == "The task is complete."


def test_invalid_json_becomes_failure():

    decision = GeminiAgentModel._parse_response(
        "this is not json"
    )

    assert decision.type == "fail"
    assert "invalid JSON" in decision.reason