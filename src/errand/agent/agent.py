from typing import Protocol

from errand.agent.context import AgentContext
from errand.agent.decision import AgentDecision
from errand.capabilities.approval import (
    CapabilityApprovalManager,
)
from errand.capabilities.generator import CapabilityGenerator
from errand.capabilities.generation_job import (
    CapabilityGenerationManager,
)
from errand.capabilities.pipeline import CapabilityPipeline
from errand.core.capability_executor import CapabilityExecutor


class AgentModel(Protocol):
    """
    Interface implemented by an LLM-backed agent model.

    The real implementation will use Gemini.
    Tests can provide a fake implementation.
    """

    def decide(
        self,
        context: AgentContext,
    ) -> AgentDecision:
        ...


class Agent:
    """
    General-purpose Errand agent.

    The agent repeatedly:

        decide -> execute -> observe -> decide

    It can also pause and ask the user for information.

    If a required capability does not exist, the agent can
    request generation of a new capability.

    Generated capabilities are NEVER trusted merely because
    Gemini produced them.

    The generation pipeline is:

        Gemini specification
            ↓
        Gemini implementation
            ↓
        static validation
            ↓
        Docker sandbox
            ↓
        explicit user approval
            ↓
        registration/persistence

    Capability generation happens asynchronously so the user
    can be asked for approval immediately while the generation
    pipeline runs in the background.
    """

    def __init__(
        self,
        model: AgentModel,
        executor: CapabilityExecutor,
        capability_generator: CapabilityGenerator | None = None,
        capability_pipeline: CapabilityPipeline | None = None,
        capability_approval_manager: (
            CapabilityApprovalManager | None
        ) = None,
        max_steps: int = 10,
    ):
        self.model = model
        self.executor = executor
        self.capability_generator = capability_generator
        self.max_steps = max_steps

        self.capability_approval_manager = (
            capability_approval_manager
        )

        # --------------------------------------------------
        # CAPABILITY PIPELINE
        # --------------------------------------------------

        if capability_pipeline is not None:

            self.capability_pipeline = capability_pipeline

        elif capability_generator is not None:

            self.capability_pipeline = CapabilityPipeline(
                generator=capability_generator,
            )

        else:

            self.capability_pipeline = None

        # --------------------------------------------------
        # ASYNC GENERATION
        # --------------------------------------------------

        if self.capability_pipeline is not None:

            self.generation_manager = (
                CapabilityGenerationManager(
                    self.capability_pipeline,
                )
            )

        else:

            self.generation_manager = None

    # ======================================================
    # PUBLIC API
    # ======================================================

    def run(
        self,
        goal: str,
    ) -> AgentDecision:
        """
        Run a complete task from scratch.

        If the agent asks the user for information, the decision
        is returned to the caller. The caller can then resume the
        same context.
        """

        context = AgentContext(
            goal=goal,
        )

        return self._run_loop(context)

    def run_context(
        self,
        context: AgentContext,
    ) -> AgentDecision:
        """
        Continue an existing task using its current context.
        """

        return self._run_loop(context)

    # ======================================================
    # MAIN LOOP
    # ======================================================

    def _run_loop(
        self,
        context: AgentContext,
    ) -> AgentDecision:

        for _ in range(self.max_steps):

            # --------------------------------------------------
            # HANDLE PENDING CAPABILITY APPROVAL
            # --------------------------------------------------

            if context.pending_capability_job is not None:

                user_message = context.last_user_message()

                if user_message is not None:

                    normalized = (
                        user_message.strip().lower()
                    )

                    # ------------------------------------------
                    # USER APPROVED
                    # ------------------------------------------

                    if normalized in {
                        "yes",
                        "y",
                        "yeah",
                        "yep",
                        "sure",
                        "okay",
                        "ok",
                    }:

                        return (
                            self._approve_pending_capability(
                                context
                            )
                        )

                    # ------------------------------------------
                    # USER REJECTED
                    # ------------------------------------------

                    if normalized in {
                        "no",
                        "n",
                        "nope",
                        "nah",
                        "cancel",
                    }:

                        return (
                            self._reject_pending_capability(
                                context
                            )
                        )

            # --------------------------------------------------
            # ASK MODEL WHAT TO DO
            # --------------------------------------------------

            decision = self.model.decide(
                context,
            )

            context.add_agent_decision(
                decision,
            )

            # --------------------------------------------------
            # ASK USER
            # --------------------------------------------------

            if decision.type == "ask_user":

                return decision

            # --------------------------------------------------
            # GENERATE CAPABILITY
            # --------------------------------------------------

            if decision.type == "generate_capability":

                return self._start_capability_generation(
                    context,
                    decision,
                )

            # --------------------------------------------------
            # CAPABILITY
            # --------------------------------------------------

            if decision.type == "capability":

                if not decision.capability:

                    return AgentDecision(
                        type="fail",
                        reason=(
                            "Agent requested a capability "
                            "without a name."
                        ),
                    )

                try:

                    result = self.executor.execute(
                        decision.capability,
                        decision.inputs,
                    )

                except Exception as exc:

                    context.add_observation(
                        {
                            "error": str(exc),
                        }
                    )

                    return AgentDecision(
                        type="fail",
                        reason=str(exc),
                    )

                context.add_observation(
                    result,
                )

                # The agent must observe the result and decide
                # what to do next.
                continue

            # --------------------------------------------------
            # FINISH
            # --------------------------------------------------

            if decision.type == "finish":

                return decision

            # --------------------------------------------------
            # FAIL
            # --------------------------------------------------

            if decision.type == "fail":

                return decision

            # --------------------------------------------------
            # UNKNOWN DECISION
            # --------------------------------------------------

            return AgentDecision(
                type="fail",
                reason=(
                    f"Unknown decision type: "
                    f"{decision.type}"
                ),
            )

        return AgentDecision(
            type="fail",
            reason=(
                f"Agent exceeded maximum number of steps "
                f"({self.max_steps})."
            ),
        )

    # ======================================================
    # START GENERATION
    # ======================================================

    def _start_capability_generation(
        self,
        context: AgentContext,
        decision: AgentDecision,
    ) -> AgentDecision:

        if self.generation_manager is None:

            return AgentDecision(
                type="fail",
                reason=(
                    "Capability generation is not configured."
                ),
            )

        if not decision.capability:

            return AgentDecision(
                type="fail",
                reason=(
                    "Agent requested capability generation "
                    "without a capability name."
                ),
            )

        if not decision.capability_description:

            return AgentDecision(
                type="fail",
                reason=(
                    "Agent requested capability generation "
                    "without a description."
                ),
            )

        # --------------------------------------------------
        # START BACKGROUND PIPELINE
        # --------------------------------------------------

        job = self.generation_manager.start(
            name=decision.capability,
            description=decision.capability_description,
        )

        context.pending_capability_job = job

        context.pending_capability_name = (
            decision.capability
        )

        context.pending_capability_description = (
            decision.capability_description
        )

        context.add_observation(
            {
                "type": "capability_generation_started",
                "name": decision.capability,
                "description": (
                    decision.capability_description
                ),
                "status": "awaiting_user_approval",
            }
        )

        # --------------------------------------------------
        # ASK USER IMMEDIATELY
        # --------------------------------------------------

        return AgentDecision(
            type="ask_user",
            question=(
                "I don't have this capability yet, "
                "but I can create one for you. "
                "Would you like me to do that?"
            ),
        )

    # ======================================================
    # APPROVE GENERATED CAPABILITY
    # ======================================================

    def _approve_pending_capability(
        self,
        context: AgentContext,
    ) -> AgentDecision:

        job = context.pending_capability_job

        if job is None:

            return AgentDecision(
                type="fail",
                reason=(
                    "There is no pending capability "
                    "generation."
                ),
            )

        # --------------------------------------------------
        # WAIT FOR BACKGROUND GENERATION
        # --------------------------------------------------

        try:

            pipeline_result = job.result()

        except Exception as exc:

            context.pending_capability_job = None
            context.pending_capability_name = None
            context.pending_capability_description = None

            return AgentDecision(
                type="fail",
                reason=(
                    "Capability generation failed: "
                    f"{exc}"
                ),
            )

        context.pending_capability_job = None

        # --------------------------------------------------
        # PIPELINE FAILED
        # --------------------------------------------------

        if not pipeline_result.passed:

            context.pending_capability_name = None
            context.pending_capability_description = None

            context.add_observation(
                {
                    "type": "capability_generation_failed",
                    "stage": pipeline_result.stage,
                    "error": pipeline_result.error,
                }
            )

            return AgentDecision(
                type="fail",
                reason=(
                    "I couldn't create the capability. "
                    f"Generation failed during "
                    f"{pipeline_result.stage}: "
                    f"{pipeline_result.error}"
                ),
            )

        # --------------------------------------------------
        # GET GENERATED CAPABILITY
        # --------------------------------------------------

        generated = pipeline_result.generated

        if generated is None:

            context.pending_capability_name = None
            context.pending_capability_description = None

            return AgentDecision(
                type="fail",
                reason=(
                    "Capability generation completed "
                    "without producing a capability."
                ),
            )

        # --------------------------------------------------
        # APPROVAL MANAGER
        # --------------------------------------------------

        if self.capability_approval_manager is None:

            return AgentDecision(
                type="fail",
                reason=(
                    "Capability approval is not configured."
                ),
            )

        # --------------------------------------------------
        # REGISTER + PERSIST
        # --------------------------------------------------

        try:

            capability = (
                self.capability_approval_manager.approve(
                    generated,
                    approved=True,
                )
            )

        except Exception as exc:

            context.add_observation(
                {
                    "type": "capability_approval_failed",
                    "error": str(exc),
                }
            )

            return AgentDecision(
                type="fail",
                reason=(
                    "The capability was generated and "
                    "tested, but I couldn't install it: "
                    f"{exc}"
                ),
            )

        # --------------------------------------------------
        # CLEAR PENDING STATE
        # --------------------------------------------------

        context.pending_capability_name = None
        context.pending_capability_description = None

        context.add_observation(
            {
                "type": "capability_approved",
                "name": capability.name,
                "status": "registered",
            }
        )

        context.add_observation(
            {
                "type": "capability_available",
                "name": capability.name,
                "message": (
                    "The requested capability has now "
                    "been installed and is available."
                ),
            }
        )

        # --------------------------------------------------
        # CONTINUE ORIGINAL TASK
        # --------------------------------------------------

        return self._continue_after_capability_install(
            context,
        )

    # ======================================================
    # REJECT GENERATED CAPABILITY
    # ======================================================

    def _reject_pending_capability(
        self,
        context: AgentContext,
    ) -> AgentDecision:

        job = context.pending_capability_job

        if job is not None:

            job.cancel()

        context.pending_capability_job = None
        context.pending_capability_name = None
        context.pending_capability_description = None

        context.add_observation(
            {
                "type": "capability_generation_cancelled",
                "status": "discarded",
            }
        )

        return AgentDecision(
            type="finish",
            result=(
                "Okay, I won't create that capability."
            ),
        )

    # ======================================================
    # CONTINUE AFTER INSTALLATION
    # ======================================================

    def _continue_after_capability_install(
        self,
        context: AgentContext,
    ) -> AgentDecision:

        """
        Resume the original task now that the capability
        exists.

        The original goal remains in context.goal.
        """

        for _ in range(self.max_steps):

            decision = self.model.decide(
                context,
            )

            context.add_agent_decision(
                decision,
            )

            if decision.type == "capability":

                if not decision.capability:

                    return AgentDecision(
                        type="fail",
                        reason=(
                            "Agent requested a capability "
                            "without a name."
                        ),
                    )

                try:

                    result = self.executor.execute(
                        decision.capability,
                        decision.inputs,
                    )

                except Exception as exc:

                    context.add_observation(
                        {
                            "error": str(exc),
                        }
                    )

                    return AgentDecision(
                        type="fail",
                        reason=str(exc),
                    )

                context.add_observation(
                    result,
                )

                continue

            if decision.type == "finish":

                return decision

            if decision.type == "ask_user":

                return decision

            if decision.type == "fail":

                return decision

            if decision.type == "generate_capability":

                return self._start_capability_generation(
                    context,
                    decision,
                )

            return AgentDecision(
                type="fail",
                reason=(
                    f"Unknown decision type: "
                    f"{decision.type}"
                ),
            )

        return AgentDecision(
            type="fail",
            reason=(
                f"Agent exceeded maximum number of steps "
                f"({self.max_steps}) while continuing "
                f"after capability installation."
            ),
        )

