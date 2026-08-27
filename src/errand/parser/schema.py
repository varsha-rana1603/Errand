from typing import Optional

from pydantic import BaseModel, Field


class ParsedField(BaseModel):
    name: str = Field(
        description="The name of an extracted field."
    )

    value: Optional[str] = Field(
        default=None,
        description=(
            "The value extracted from the user's command. "
            "Use null when the user did not provide the value."
        ),
    )


class ParsedIntent(BaseModel):
    action: str = Field(
        description=(
            "A concise identifier describing what the user wants "
            "Errand to do, such as play_music, open_url, or send_email."
        )
    )

    fields: list[ParsedField] = Field(
        default_factory=list,
        description=(
            "Information extracted from the user's command."
        ),
    )