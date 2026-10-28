import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.finding import FindingSchema
from app.services.orchestrator import Orchestrator

# Helper to create a simple FindingSchema
def make_finding(file_path: str, line: int | None, severity: str, confidence: str, description: str):
    return FindingSchema(
        file_path=file_path,
        line_number=line,
        severity=severity,
        confidence=confidence,
        description=description,
        evidence="evidence",
        suggestion="suggestion",
    )

@pytest.mark.asyncio
async def test_orchestrator_all_success():
    diff = "dummy diff"
    # Mock each agent to return a distinct finding
    sec_f = make_finding("sec.py", 10, "high", "high", "sec issue")
    perf_f = make_finding("perf.py", 20, "medium", "medium", "perf issue")
    cq_f = make_finding("cq.py", 30, "low", "low", "code quality issue")
    cov_f = make_finding("cov.py", 40, "high", "low", "coverage issue")

    with (
        patch("app.services.orchestrator.review_security", AsyncMock(return_value=[sec_f])),
        patch("app.services.orchestrator.review_performance", AsyncMock(return_value=[perf_f])),
        patch("app.services.orchestrator.review_code_quality", AsyncMock(return_value=[cq_f])),
        patch("app.services.orchestrator.review_test_coverage", AsyncMock(return_value=[cov_f])),
    ):
        orchestrator = Orchestrator(concurrency=2, per_agent_timeout=2)
        result = await orchestrator.review(diff)

    # All agents succeeded
    assert result["agent_statuses"] == {"security": "success", "performance": "success", "code_quality": "success", "test_coverage": "success"}
    # Findings should be sorted by severity then confidence (high>medium>low)
    # Expected order: sec_f (high/high), cov_f (high/low), perf_f (medium/medium), cq_f (low/low)
    sorted_desc = [f.description for f in result["findings"]]
    assert sorted_desc == ["sec issue", "coverage issue", "perf issue", "code quality issue"]

@pytest.mark.asyncio
async def test_orchestrator_duplicate_and_error():
    diff = "dummy diff"
    dup_f1 = make_finding("dup.py", 1, "medium", "medium", "duplicate issue")
    dup_f2 = make_finding("dup.py", 1, "medium", "medium", "duplicate issue")  # same key
    err_f = make_finding("err.py", 2, "low", "low", "error issue")

    async def raise_error(_):
        raise RuntimeError("boom")

    with (
        patch("app.services.orchestrator.review_security", AsyncMock(return_value=[dup_f1])),
        patch("app.services.orchestrator.review_performance", AsyncMock(return_value=[dup_f2])),
        patch("app.services.orchestrator.review_code_quality", AsyncMock(side_effect=raise_error)),
        patch("app.services.orchestrator.review_test_coverage", AsyncMock(return_value=[err_f])),
    ):
        orchestrator = Orchestrator(concurrency=2, per_agent_timeout=2)
        result = await orchestrator.review(diff)

    # Duplicate should appear only once
    assert len(result["findings"]) == 2
    descriptions = {f.description for f in result["findings"]}
    assert descriptions == {"duplicate issue", "error issue"}
    # status for code_quality should be error, others success
    assert result["agent_statuses"]["code_quality"] == "error"
    assert "boom" in result["errors"][0]

@pytest.mark.asyncio
async def test_orchestrator_timeout():
    diff = "dummy diff"
    slow_f = make_finding("slow.py", 3, "high", "high", "slow issue")

    async def slow_agent(_):
        await asyncio.sleep(0.2)  # longer than timeout we set
        return [slow_f]

    with (
        patch("app.services.orchestrator.review_security", AsyncMock(return_value=[])),
        patch("app.services.orchestrator.review_performance", slow_agent),
        patch("app.services.orchestrator.review_code_quality", AsyncMock(return_value=[])),
        patch("app.services.orchestrator.review_test_coverage", AsyncMock(return_value=[])),
    ):
        orchestrator = Orchestrator(concurrency=2, per_agent_timeout=0.05)
        result = await orchestrator.review(diff)

    assert result["agent_statuses"]["performance"] == "timeout"
    assert any("timed out" in e for e in result["errors"])
