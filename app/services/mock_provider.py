from app.services.provider import LLMProvider
from app.schemas.finding import FindingSchema
import re
from typing import List

class MockProvider(LLMProvider):
    """Deterministic mock LLM provider for testing.

    It analyses the supplied code string and returns findings based on simple
    keyword patterns. This implementation does **not** call any external API
    and is fully deterministic, making it safe for unit tests.
    """

    async def analyze_code(self, code: str) -> List[FindingSchema]:
        # Simple deterministic behavior: if the code contains the marker
        # "MOCK_ERROR" raise an exception to simulate provider failure.
        if "MOCK_ERROR" in code:
            raise RuntimeError("Simulated provider error")

        findings: List[FindingSchema] = []
        # Example deterministic rule: if the code contains the string
        # "UNSAFE_PATTERN" we return a dummy finding.
        if "UNSAFE_PATTERN" in code:
            findings.append(
                FindingSchema(
                    file_path="unknown",
                    line_number=None,
                    severity="high",
                    confidence="high",
                    description="Detected unsafe pattern",
                    evidence="UNSAFE_PATTERN",
                    suggestion="Remove the unsafe pattern",
                    metadata={"source": "mock"},
                )
            )
        return findings
