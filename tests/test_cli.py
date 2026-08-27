from errand.cli.main import run_command
from errand.core.intent import Intent
from errand.skills.defaults import create_default_registry


class FakeParser:

    def parse(self, command):

        return Intent(
            action="open_app",
            fields={},
        )


def test_cli_can_handle_agent_question(monkeypatch, capsys):

    class FakeModel:

        def decide(self, context):
            from errand.agent.decision import AgentDecision

            return AgentDecision(
                type="ask_user",
                question="Which application would you like me to open?",
            )

    run_command(
        "open an app",
        model=FakeModel(),
    )

    output = capsys.readouterr().out

    assert "Which application would you like me to open?" in output

def test_cli_uses_agent_flow(monkeypatch, capsys):

    class FakeAgent:

        def __init__(self, model, executor):
            self.model = model
            self.executor = executor

        def run(self, goal):
            from errand.agent.decision import AgentDecision

            return AgentDecision(
                type="finish",
                result="Task completed.",
            )

    class FakeModel:
        pass

    monkeypatch.setattr(
        "errand.cli.main.Agent",
        FakeAgent,
    )

    monkeypatch.setattr(
        "errand.cli.main.GeminiAgentModel",
        lambda registry: FakeModel(),
    )

    run_command("do something")

    output = capsys.readouterr().out

    assert "Task completed." in output

