import pytest
from app.services.coverage_agent import review_test_coverage

@pytest.mark.asyncio
async def test_missing_test_detection():
    diff = """
--- a/example.py
+++ b/example.py
@@ -0,0 +1,5 @@
+def new_feature(x, y):
+    return x + y
"""
    findings = await review_test_coverage(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "medium"
    assert f.description.startswith("Added function")
    assert "new_feature" in f.description

@pytest.mark.asyncio
async def test_with_test_present_no_finding():
    diff = """
--- a/example.py
+++ b/example.py
@@ -0,0 +1,5 @@
+def compute(val):
+    return val * 2
+def test_compute():
+    assert compute(3) == 6
"""
    findings = await review_test_coverage(diff)
    assert len(findings) == 0
