from abc import ABC, abstractmethod
from typing import List
from app.schemas.finding import FindingSchema

class LLMProvider(ABC):
    """Abstract base class for LLM based code analysis providers."""

    @abstractmethod
    async def analyze_code(self, code: str) -> List[FindingSchema]:
        """Analyze the given source code and return a list of findings.

        Args:
            code: The source code string to be analyzed.
        Returns:
            A list of :class:`FindingSchema` instances describing issues.
        """
        raise NotImplementedError
