from abc import ABC, abstractmethod
from errand.core.intent import Intent

class Parser(ABC):
    @abstractmethod
    def parse(self, text: str) -> Intent:
        #Convert natural-language into structured Intent
        pass

    