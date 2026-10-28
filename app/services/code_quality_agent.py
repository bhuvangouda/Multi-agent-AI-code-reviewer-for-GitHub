import ast
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
            metadata=metadata or {"agent": "code_quality"},
        )
    )


def _is_complex(func_node: ast.FunctionDef, threshold: int = 4) -> bool:
    """Estimate cyclomatic complexity by counting branching statements."""
    count = 0
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncFor, ast.AsyncWith)):
            count += 1
    return count > threshold


async def review_code_quality(diff: str) -> List[FindingSchema]:
    """Analyze a unified diff for code quality issues.

    Detects duplicated added lines, bare ``except:`` clauses, and functions with high cyclomatic complexity.
    """
    findings: List[FindingSchema] = []
    added_lines: List[tuple[int, str]] = []
    for i, line in enumerate(diff.splitlines(), start=1):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:]
        added_lines.append((i, added))
        # Duplicate line detection
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
                    description="Repeated identical added line – may indicate duplicated logic",
                    evidence=txt.strip(),
                    suggestion="Refactor to a shared helper",
                )
                break
        # Bare except detection
        if re.match(r"\s*except\s*:\s*$", added):
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i,
                severity="medium",
                confidence="high",
                description="Bare except clause without specifying exception type",
                evidence=added.strip(),
                suggestion="Specify the exception type to avoid swallowing errors",
            )

        # Function complexity detection
        if added.startswith("def "):
            # capture function definition and its indented body
            func_buffer = [added]
            func_start_line = i
            # look ahead in the diff lines
            diff_lines = diff.splitlines()
            for next_idx in range(i, len(diff_lines)):
                next_line = diff_lines[next_idx]
                if not next_line.startswith('+') or next_line.startswith('+++'):
                    break
                next_added = next_line[1:]
                if next_added.startswith('    ') or next_added.startswith('\t'):
                    func_buffer.append(next_added)
                else:
                    break
            try:
                node = ast.parse("\n".join(func_buffer)).body[0]
                if isinstance(node, ast.FunctionDef) and _is_complex(node):
                    _add_finding(
                        findings,
                        file_path="unknown",
                        line_number=func_start_line,
                        severity="high",
                        confidence="medium",
                        description="Function has high cyclomatic complexity",
                        evidence=" ".join(func_buffer[:2]),
                        suggestion="Refactor into smaller units",
                    )
            except Exception:
                pass

    return findings
