import pytest
from app.services.performance_agent import review_performance

@pytest.mark.asyncio
async def test_n_plus_one_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,3 @@
+for user in users:
+    db.session.query(User).filter(User.id == user.id)
+    # some other line
+"""
    findings = await review_performance(diff)
    assert any(f.severity == "high" and "N+1" in f.description for f in findings)
    # The detection should point to the line with query (line 3 in diff)
    n1_finding = next(f for f in findings if "N+1" in f.description)
    assert n1_finding.line_number == 3

@pytest.mark.asyncio
async def test_duplicate_lines_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,3 @@
+expensive_calc()
+expensive_calc()
+expensive_calc()
+"""
    findings = await review_performance(diff)
    assert any(f.severity == "low" and "Repeated identical" in f.description for f in findings)

@pytest.mark.asyncio
async def test_network_inside_loop_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,2 @@
+for item in items:
+    requests.get(item.url)
+"""
    findings = await review_performance(diff)
    assert any(f.severity == "high" and "Network request inside loop" in f.description for f in findings)

@pytest.mark.asyncio
async def test_sleep_inside_loop_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,3 @@
+for i in range(5):
+    time.sleep(1)
+    process(i)
+"""
    findings = await review_performance(diff)
    assert any(f.severity == "medium" and "sleep call" in f.description for f in findings)

@pytest.mark.asyncio
async def test_no_findings_safe_code():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,2 @@
+def add(a, b):
+    return a + b
+"""
    findings = await review_performance(diff)
    assert findings == []
