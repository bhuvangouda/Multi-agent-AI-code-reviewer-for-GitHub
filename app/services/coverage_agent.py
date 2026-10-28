import re
from typing import List

from app.schemas.finding import FindingSchema


def _add_finding(findings: List[FindingSchema], *, file_path: str, line_number: int | None, severity: str, confidence: str, description: str, evidence: str, suggestion: str | None = None, metadata: dict | None = None):
    findings.append(
        FindingSchema(
            file_path=file_path,
            line_number=line_number,
            severity=severity,
            confidence=confidence,
            description=description,
            evidence=evidence,
            suggestion=suggestion,
            metadata=metadata or {"agent": "test_coverage"},
        )
    )


async def review_test_coverage(diff: str) -> List[FindingSchema]:
    """Analyze a unified diff for potential test coverage gaps.

    Heuristic:
    * For each added function (def <name>(...)) that is not a test (doesn't start with test_), check if a corresponding test function
      def test_<name>(...) is also added in the diff.
    * If no matching test is found, emit a finding recommending adding tests.
    """
    findings: List[FindingSchema] = []
    added_functions: List[tuple[int, str]] = []
    added_tests: set[str] = set()
    func_pattern = re.compile(r"^def\s+(\w+)\s*\(")
    test_pattern = re.compile(r"^def\s+test_(\w+)\s*\(")
    for i, line in enumerate(diff.splitlines(), start=1):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:]
        m = func_pattern.match(added)
        if m:
            name = m.group(1)
            added_functions.append((i, name))
        t = test_pattern.match(added)
        if t:
            added_tests.add(t.group(1))
    for line_no, func_name in added_functions:
        if func_name.startswith("test_"):
            continue
        if func_name not in added_tests:
            _add_finding(
                findings,
                file_path="unknown",
                line_number=line_no,
                severity="medium",
                confidence="medium",
                description=f"Added function '{func_name}' lacks a test",
                evidence=func_name,
                suggestion=f"Add a test function test_{func_name} to cover this code",
            )
    return findings
