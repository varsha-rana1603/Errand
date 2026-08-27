import subprocess

from errand.capabilities.base import Capability


class OpenAppCapability(Capability):

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Open a macOS application."

    @property
    def input_schema(self) -> dict[str, type]:
        return {
            "app_name": str,
        }

    def execute(self, inputs: dict) -> str:
        app_name = inputs["app_name"]

        subprocess.run(
            ["open", "-a", app_name],
            check=True,
        )

        return f"Opened {app_name}."