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
            metadata=metadata or {"agent": "performance"},
        )
    )


async def review_performance(diff: str) -> List[FindingSchema]:
    """Analyze a unified diff for performance issues.

    Heuristics include:
    * Potential N+1 database query patterns (a ``for`` loop with a ``.query`` or ``.filter`` call on the next line).
    * Repeated identical added lines (possible duplicated expensive computation).
    * Network calls inside loops (e.g., ``requests.get`` inside a ``for`` loop).
    * Use of ``time.sleep`` inside loops.
    """
    findings: List[FindingSchema] = []
    added_lines: List[tuple[int, str]] = []
    prev_loop_line: int | None = None
    for i, line in enumerate(diff.splitlines(), start=1):
        if not line.startswith('+') or line.startswith('+++'):
            continue
        added = line[1:]
        added_lines.append((i, added))
        # Detect duplicated added lines (any repeats up to this point)
        counts = {}
        for _, txt in added_lines:
            counts[txt] = counts.get(txt, 0) + 1
        for txt, cnt in counts.items():
            if cnt > 1:
                _add_finding(
                    findings,
                    file_path="unknown",
                    line_number=None,
                    severity="low",
                    confidence="low",
                    description="Repeated identical added line – may indicate redundant computation",
                    evidence=txt.strip(),
                    suggestion="Consolidate duplicated code",
                )
                break
        # Check if this line starts a for-loop
        if re.search(r"for .+ in .+:", added):
            prev_loop_line = i
            continue
        # If previous line was a for-loop, examine this line for patterns
        if prev_loop_line is not None:
            # time.sleep detection
            if re.search(r"time\.sleep\s*\(", added):
                _add_finding(
                    findings,
                    file_path="unknown",
                    line_number=i,
                    severity="medium",
                    confidence="high",
                    description="Blocking sleep call inside loop",
                    evidence=added.strip(),
                    suggestion="Consider async sleep or avoid sleeping in performance-critical loops",
                )
            # network request detection
            if re.search(r"requests\.(get|post|put|delete)\s*\(", added):
                _add_finding(
                    findings,
                    file_path="unknown",
                    line_number=i,
                    severity="high",
                    confidence="high",
                    description="Network request inside loop may cause performance degradation",
                    evidence=added.strip(),
                    suggestion="Batch requests or move outside the loop",
                )
            # N+1 query detection
            if re.search(r"\.query\s*\(|\.filter\s*\(", added):
                # calculate added line index (excluding diff headers)
                added_index = sum(1 for _, _ in added_lines if _ is not None)
                line_number = added_index + 1
                _add_finding(
                    findings,
                    file_path="unknown",
                    line_number=line_number,
                    severity="high",
                    confidence="medium",
                    description="Possible N+1 database query pattern",
                    evidence=added.strip(),
                    suggestion="Prefetch data or use bulk query",
                )
            # Reset after handling the line following a loop
            prev_loop_line = None
    return findings
