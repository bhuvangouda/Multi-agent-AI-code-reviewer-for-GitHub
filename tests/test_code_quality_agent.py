import pytest
from app.services.code_quality_agent import review_code_quality

@pytest.mark.asyncio
async def test_duplicate_lines_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,3 @@
+expensive_calc()
+expensive_calc()
+expensive_calc()
+"""
    findings = await review_code_quality(diff)
    assert any(f.severity == "low" and "Repeated identical" in f.description for f in findings)

@pytest.mark.asyncio
async def test_bare_except_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,2 @@
+try:
+    something()
+except:
+    pass
+"""
    findings = await review_code_quality(diff)
    assert any(f.severity == "medium" and "Bare except" in f.description for f in findings)

@pytest.mark.asyncio
async def test_complex_function_detection():
    diff = """--- a/file.py
+++ b/file.py
@@ -1,0 +1,12 @@
+def complex_func(x):
+    if x > 0:
+        for i in range(10):
+            try:
+                if i % 2 == 0:
+                    print(i)
+                else:
+                    raise ValueError()
+            except Exception:
+                pass
+    else:
+        while x < 0:
+            x += 1
+"""
    findings = await review_code_quality(diff)
    assert any(f.severity == "high" and "high cyclomatic complexity" in f.description for f in findings)
