import time

from errand.capabilities.generation_job import (
    CapabilityGenerationManager,
)


class FakePipeline:

    def __init__(self):
        self.called = False

    def run(self, name, description):
        self.called = True

        time.sleep(0.05)

        return {
            "name": name,
            "description": description,
        }


def test_generation_starts_in_background():

    pipeline = FakePipeline()

    manager = CapabilityGenerationManager(
        pipeline
    )

    job = manager.start(
        name="play_music",
        description="Play music.",
    )

    # The call to start() should return a job rather than
    # waiting for the pipeline to finish.
    assert job is not None

    result = job.result()

    assert result == {
        "name": "play_music",
        "description": "Play music.",
    }

    assert pipeline.called is True


def test_generation_job_reports_completion():

    pipeline = FakePipeline()

    manager = CapabilityGenerationManager(
        pipeline
    )

    job = manager.start(
        name="play_music",
        description="Play music.",
    )

    assert job.done is False

    job.result()

    assert job.done is True


def test_generation_job_can_be_cancelled():

    pipeline = FakePipeline()

    manager = CapabilityGenerationManager(
        pipeline
    )

    job = manager.start(
        name="play_music",
        description="Play music.",
    )

    job.cancel()

    assert job.cancelled is True