import argparse

from dotenv import load_dotenv

from errand.agent.agent import Agent
from errand.agent.context import AgentContext
from errand.agent.gemini import GeminiAgentModel
from errand.capabilities.defaults import create_default_capability_registry
from errand.core.capability_executor import CapabilityExecutor


load_dotenv()


def run_command(command, model=None, registry=None):

    if registry is None:
        registry = create_default_capability_registry()

    executor = CapabilityExecutor(registry)

    model_was_provided = model is not None

    if model is None:
        model = GeminiAgentModel(registry)

    agent = Agent(
        model=model,
        executor=executor,
    )

    # --------------------------------------------------
    # Backwards-compatible test / injected-agent flow
    # --------------------------------------------------

    if not hasattr(agent, "run_context"):

        decision = agent.run(command)

        if decision.type == "finish":

            if decision.result:
                print(decision.result)

        elif decision.type == "ask_user":

            print(decision.question)

        elif decision.type == "fail":

            print(
                f"Sorry, I couldn't complete that task: "
                f"{decision.reason}"
            )

        return

    # --------------------------------------------------
    # Interactive agent flow
    # --------------------------------------------------

    context = AgentContext(goal=command)

    while True:

        decision = agent.run_context(context)

        # ----------------------------------------------
        # ASK USER
        # ----------------------------------------------

        if decision.type == "ask_user":

            # When a model is explicitly supplied by a test,
            # preserve the old non-interactive behavior.
            if model_was_provided:
                print(decision.question)
                return

            answer = input(f"{decision.question} ")

            context.add_user_message(answer)

            continue

        # ----------------------------------------------
        # FINISH
        # ----------------------------------------------

        if decision.type == "finish":

            if decision.result:
                print(decision.result)

            return

        # ----------------------------------------------
        # FAIL
        # ----------------------------------------------

        if decision.type == "fail":

            print(
                f"Sorry, I couldn't complete that task: "
                f"{decision.reason}"
            )

            return


def main(argv=None):

    parser = argparse.ArgumentParser(
        prog="errand",
        description="Natural-language command tool for macOS",
    )

    parser.add_argument(
        "command",
        nargs="+",
        help="The natural-language command to execute",
    )

    args = parser.parse_args(argv)

    command = " ".join(args.command)

    run_command(command)


if __name__ == "__main__":
    main()
