from dataclasses import dataclass
from typing import Any

@dataclass
class Intent: 
    action: str
    fields: dict[str, Any]

