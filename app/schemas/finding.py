from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class FindingSchema(BaseModel):
    """Pydantic model representing a code review finding."""

    file_path: str = Field(..., description="Relative path to the file containing the issue")
    line_number: Optional[int] = Field(None, description="Line number where the issue occurs, if applicable")
    severity: str = Field(..., description="Severity level (e.g., low, medium, high, critical)")
    confidence: str = Field(..., description="Confidence level (e.g., low, medium, high)")
    description: str = Field(..., description="Human‑readable description of the problem")
    evidence: str = Field(..., description="Snippet or evidence that demonstrates the issue")
    suggestion: Optional[str] = Field(None, description="Suggested remediation or fix")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary additional data")
