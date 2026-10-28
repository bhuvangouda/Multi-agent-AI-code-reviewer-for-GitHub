import asyncio
from typing import List, Dict, Any

from app.schemas.finding import FindingSchema
from app.services.security_agent import review_security
from app.services.performance_agent import review_performance
from app.services.code_quality_agent import review_code_quality
from app.services.coverage_agent import review_test_coverage

# Helper ordering for severity and confidence
_SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}
_CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}

class Orchestrator:
    """Runs multiple review agents on a diff and aggregates findings.

    Features:
    * Concurrency control via semaphore.
    * Per‑agent timeout to avoid blocking.
    * Graceful handling of exceptions – other agents continue.
    * Validation against ``FindingSchema``.
    * Deduplication of identical findings.
    * Ranking of findings by severity then confidence.
    """

    def __init__(self, concurrency: int = 3, per_agent_timeout: int = 5):
        self.concurrency = concurrency
        self.per_agent_timeout = per_agent_timeout
        self._semaphore = asyncio.Semaphore(concurrency)
        self._agents = {
            "security": review_security,
            "performance": review_performance,
            "code_quality": review_code_quality,
            "test_coverage": review_test_coverage,
        }

    async def _run_agent(self, name: str, func, diff: str) -> Dict[str, Any]:
        async with self._semaphore:
            try:
                findings: List[FindingSchema] = await asyncio.wait_for(func(diff), timeout=self.per_agent_timeout)
                # Validate each finding conforms to schema (basic attribute check)
                for f in findings:
                    if not isinstance(f, FindingSchema):
                        raise TypeError(f"Agent {name} returned non‑FindingSchema object")
                return {"status": "success", "findings": findings}
            except asyncio.TimeoutError:
                return {"status": "timeout", "error": f"Agent {name} timed out after {self.per_agent_timeout}s"}
            except Exception as exc:  # pylint: disable=broad-except
                return {"status": "error", "error": str(exc)}

    async def review(self, diff: str, context: dict | None = None) -> Dict[str, Any]:
        """Run all agents on *diff* and return an aggregated result.

        Returns a dict with:
        * ``findings`` – list of deduplicated, sorted ``FindingSchema`` objects.
        * ``agent_statuses`` – mapping of agent name to ``status`` (success, error, timeout).
        * ``errors`` – optional list of error messages for agents that failed.
        """
        tasks = [self._run_agent(name, func, diff) for name, func in self._agents.items()]
        results = await asyncio.gather(*tasks)

        aggregated_findings: List[FindingSchema] = []
        agent_statuses: Dict[str, str] = {}
        errors: List[str] = []
        seen: set[tuple] = set()

        for (name, _), res in zip(self._agents.items(), results):
            agent_statuses[name] = res["status"]
            if res["status"] == "success":
                for f in res["findings"]:
                    key = (f.file_path, f.line_number, f.description)
                    if key not in seen:
                        seen.add(key)
                        aggregated_findings.append(f)
            else:
                errors.append(res.get("error", f"Agent {name} failed"))

        # Sort findings by severity then confidence (high → low)
        def sort_key(f: FindingSchema):
            return (-_SEVERITY_ORDER.get(f.severity, 0), -_CONFIDENCE_ORDER.get(f.confidence, 0))

        aggregated_findings.sort(key=sort_key)

        return {
            "findings": aggregated_findings,
            "agent_statuses": agent_statuses,
            "errors": errors,
        }
