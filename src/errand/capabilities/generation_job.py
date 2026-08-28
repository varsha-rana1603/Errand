from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

from errand.capabilities.pipeline import (
    CapabilityPipeline,
    CapabilityPipelineResult,
)


@dataclass
class CapabilityGenerationJob:
    """
    Represents one background capability-generation operation.

    The pipeline runs independently while the user decides whether
    they want Errand to install the capability.
    """

    executor: ThreadPoolExecutor
    future: Future | None = None
    stage: str = "starting"

    def __post_init__(self):
        self._cancelled = False
        self._lock = Lock()

    def set_stage(self, stage: str) -> None:
        with self._lock:
            self.stage = stage

    def cancel(self) -> None:
        """
        Mark this generation as cancelled.

        If the pipeline has already started, the underlying work may
        still finish. Its result must then be discarded and must never
        be approved or registered.
        """

        with self._lock:
            self._cancelled = True

        if self.future is not None:
            self.future.cancel()

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    @property
    def done(self) -> bool:
        if self.future is None:
            return False

        return self.future.done()

    def result(self) -> CapabilityPipelineResult:
        """
        Wait for the background pipeline and return its result.
        """

        if self.future is None:
            raise RuntimeError(
                "Generation job has not been started."
            )

        try:
            return self.future.result()

        finally:
            self.executor.shutdown(
                wait=False
            )


class CapabilityGenerationManager:
    """
    Starts capability-generation pipelines in the background.
    """

    def __init__(
        self,
        pipeline: CapabilityPipeline,
    ):
        self.pipeline = pipeline

    def start(
        self,
        name: str,
        description: str,
    ) -> CapabilityGenerationJob:

        executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="errand-capability",
        )

        job = CapabilityGenerationJob(
            executor=executor,
        )

        future = executor.submit(
            self._run_pipeline,
            job,
            name,
            description,
        )

        job.future = future

        return job

    def _run_pipeline(
        self,
        job: CapabilityGenerationJob,
        name: str,
        description: str,
    ) -> CapabilityPipelineResult:

        job.set_stage(
            "specification_generation"
        )

        try:
            return self.pipeline.run(
                name,
                description,
                stage_callback=job.set_stage,
            )

        except TypeError as exc:

            if "stage_callback" not in str(exc):
                raise

            # Backwards compatibility with pipeline
            # implementations that don't support stage callbacks yet.
            return self.pipeline.run(
                name,
                description,
            )