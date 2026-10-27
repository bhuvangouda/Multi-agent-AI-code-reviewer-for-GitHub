import re
import asyncio
from typing import List

from app.schemas.finding import FindingSchema
from app.services.provider import LLMProvider


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
            metadata=metadata or {"agent": "security"},
        )
    )


async def _run_provider(provider: LLMProvider, code: str) -> List[FindingSchema]:
    try:
        return await provider.analyze_code(code)
    except Exception as e:
        # Simulate graceful handling: return empty list and log error
        # Logging omitted for brevity
        return []


async def review_security(diff: str, provider: LLMProvider) -> List[FindingSchema]:
    """Analyze a code diff for security issues.

    The function performs deterministic regex‑based checks on added lines
    (those prefixed with ``+`` in a unified diff). It also delegates to the
    supplied ``LLMProvider`` for contextual analysis. All findings are
    returned as a list of :class:`FindingSchema` instances.
    """
    findings: List[FindingSchema] = []

    # Split diff into lines and iterate
    for i, line in enumerate(diff.splitlines(), start=1):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        # Remove the leading '+'
        added = line[1:]
        # Simple rule: concatenated SQL strings → possible injection
        if re.search(r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*['\"]\s*\+", added, re.IGNORECASE):
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i-1,
                severity="high",
                confidence="high",
                description="Potential SQL injection via string concatenation",
                evidence=added.strip(),
                suggestion="Use parameterised queries instead",
            )
        # Command injection via os.system or subprocess with variable
        if re.search(r"(os\.system|subprocess\.run)\s*\(.*\+.*\)", added):
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i-1,
                severity="high",
                confidence="high",
                description="Potential command injection",
                evidence=added.strip(),
                suggestion="Avoid concatenating user input into shell commands",
            )
        # Hard‑coded secret detection (simple heuristic)
        secret_match = re.search(r"(API_KEY|PASSWORD|SECRET|TOKEN)\s*=\s*['\"]([^'\"]{4,})['\"]", added, re.IGNORECASE)
        if secret_match:
            key_name = secret_match.group(1)
            # Redact the value
            redacted = "[REDACTED]"
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i-1,
                severity="critical",
                confidence="high",
                description=f"Hard‑coded secret detected: {key_name}",
                evidence=f"{key_name} = {redacted}",
                suggestion="Move secret to environment variables or secret manager",
            )
        # Unsafe deserialization (pickle usage)
        if re.search(r"pickle\.loads\s*\(", added):
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i-1,
                severity="high",
                confidence="medium",
                description="Unsafe deserialization using pickle",
                evidence=added.strip(),
                suggestion="Prefer safe serialization formats like json",
            )
        # Dangerous file operation (write to arbitrary path)
        if re.search(r"open\s*\(.*['\"]w['\"]\)", added):
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i-1,
                severity="medium",
                confidence="medium",
                description="Potential unsafe file write",
                evidence=added.strip(),
                suggestion="Validate file paths before writing",
            )
        # Simple auth/authorization check (hard‑coded admin flag)
        if re.search(r"if\s+user\.is_admin\s*:\s*pass", added):
            _add_finding(
                findings,
                file_path="unknown",
                line_number=i,
                severity="low",
                confidence="low",
                description="Potential missing authorization check",
                evidence=added.strip(),
                suggestion="Implement proper permission checks",
            )

    # Run LLM provider for additional context (deterministic mock will add its own findings)
    provider_findings = await _run_provider(provider, diff)
    findings.extend(provider_findings)
    return findings
