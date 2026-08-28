import argparse
import time

from dotenv import load_dotenv

from errand.agent.agent import Agent
from errand.agent.context import AgentContext
from errand.agent.gemini import GeminiAgentModel
from errand.capabilities.approval import (
    CapabilityApprovalManager,
)
from errand.capabilities.defaults import (
    create_default_capability_registry,
)
from errand.capabilities.generator import CapabilityGenerator
from errand.core.capability_executor import CapabilityExecutor


load_dotenv()


APPROVAL_WORDS = {
    "yes",
    "y",
    "yeah",
    "yep",
    "sure",
    "okay",
    "ok",
}

REJECTION_WORDS = {
    "no",
    "n",
    "nope",
    "nah",
    "cancel",
}


def wait_for_capability_generation(
    context: AgentContext,
) -> None:
    """
    Wait for a pending capability-generation job while
    displaying simple progress feedback.

    The generation itself is already running in the background.
    This function only provides user-facing progress feedback.
    """

    job = context.pending_capability_job

    if job is None:
        return

    print(
        "\nCreating capability...",
        flush=True,
    )

    last_stage = None

    while not job.done:

        stage = getattr(
            job,
            "stage",
            None,
        )

        if stage != last_stage:

            if stage == "specification_generation":
                print(
                    "  → Generating capability specification...",
                    flush=True,
                )

            elif stage == "code_generation":
                print(
                    "  → Generating capability code...",
                    flush=True,
                )

            elif stage == "static_validation":
                print(
                    "  → Running static security validation...",
                    flush=True,
                )

            elif stage == "sandbox_execution":
                print(
                    "  → Testing capability in Docker sandbox...",
                    flush=True,
                )

            elif stage == "completed":
                print(
                    "  → Capability generation completed.",
                    flush=True,
                )

            elif stage is not None:
                print(
                    f"  → {stage}...",
                    flush=True,
                )

            last_stage = stage

        time.sleep(0.1)

    # Make sure the user sees completion even if the final
    # stage transition happened immediately before job.done.
    final_stage = getattr(
        job,
        "stage",
        None,
    )

    if final_stage == "completed" and last_stage != "completed":
        print(
            "  → Capability generation completed.",
            flush=True,
        )


def run_command(
    command,
    model=None,
    registry=None,
):

    if registry is None:
        registry = create_default_capability_registry()

    executor = CapabilityExecutor(
        registry,
    )

    model_was_provided = model is not None

    if model is None:
        model = GeminiAgentModel(
            registry,
        )

    capability_generator = CapabilityGenerator()

    approval_manager = CapabilityApprovalManager(
        registry=registry,
    )

    try:

        agent = Agent(
            model=model,
            executor=executor,
            capability_generator=capability_generator,
            capability_approval_manager=approval_manager,
        )

    except TypeError:

        # Backwards compatibility for injected test agents.
        agent = Agent(
            model=model,
            executor=executor,
        )

    # --------------------------------------------------
    # BACKWARDS-COMPATIBLE TEST / INJECTED-AGENT FLOW
    # --------------------------------------------------

    if not hasattr(agent, "run_context"):

        decision = agent.run(
            command,
        )

        if decision.type == "finish":

            if decision.result:
                print(
                    decision.result
                )

        elif decision.type == "ask_user":

            print(
                decision.question
            )

        elif decision.type == "fail":

            print(
                f"Sorry, I couldn't complete that task: "
                f"{decision.reason}"
            )

        return

    # --------------------------------------------------
    # INTERACTIVE AGENT FLOW
    # --------------------------------------------------

    context = AgentContext(
        goal=command,
    )

    while True:

        decision = agent.run_context(
            context,
        )

        # ----------------------------------------------
        # ASK USER
        # ----------------------------------------------

        if decision.type == "ask_user":

            # Preserve non-interactive behaviour for
            # injected test models.
            if model_was_provided:

                print(
                    decision.question
                )

                return

            answer = input(
                f"{decision.question} "
            ).strip()

            context.add_user_message(
                answer,
            )

            normalized = answer.lower()

            # ------------------------------------------
            # USER APPROVED PENDING CAPABILITY
            # ------------------------------------------

            if (
                context.pending_capability_job is not None
                and normalized in APPROVAL_WORDS
            ):

                wait_for_capability_generation(
                    context,
                )

            # ------------------------------------------
            # USER REJECTED PENDING CAPABILITY
            # ------------------------------------------

            elif (
                context.pending_capability_job is not None
                and normalized in REJECTION_WORDS
            ):

                # Agent handles cancellation and cleanup
                # when run_context() is called again.
                pass

            continue

        # ----------------------------------------------
        # FINISH
        # ----------------------------------------------

        if decision.type == "finish":

            if decision.result:

                print(
                    decision.result
                )

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

        # ----------------------------------------------
        # SAFETY FALLBACK
        # ----------------------------------------------

        print(
            "Sorry, Errand returned an unexpected state."
        )

        return


def main(
    argv=None,
):

    parser = argparse.ArgumentParser(
        prog="errand",
        description=(
            "Natural-language command tool for macOS"
        ),
    )

    parser.add_argument(
        "command",
        nargs="+",
        help=(
            "The natural-language command "
            "to execute"
        ),
    )

    args = parser.parse_args(
        argv,
    )

    command = " ".join(
        args.command,
    )

    run_command(
        command,
    )


if __name__ == "__main__":
    main()

