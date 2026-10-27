import pytest
from app.services.security_agent import review_security
from app.services.mock_provider import MockProvider

@pytest.mark.asyncio
async def test_sql_injection_finding():
    diff = """--- a/file.py\n+++ b/file.py\n@@ -1,0 +1,1 @@\n+query = \"SELECT * FROM users WHERE id = \" + user_input\n"""
    findings = await review_security(diff, MockProvider())
    assert any(f.severity == "high" and "SQL injection" in f.description for f in findings)
    inj = next(f for f in findings if f.severity == "high" and "SQL injection" in f.description)
    assert inj.line_number == 3

@pytest.mark.asyncio
async def test_command_injection_finding():
    diff = """--- a/run.py\n+++ b/run.py\n@@ -10,0 +11,1 @@\n+os.system(\"rm -rf /\" + user_input)\n"""
    findings = await review_security(diff, MockProvider())
    assert any(f.severity == "high" and "command injection" in f.description.lower() for f in findings)
    cmd = next(f for f in findings if f.severity == "high" and "command injection" in f.description.lower())
    assert cmd.line_number == 3

@pytest.mark.asyncio
async def test_hardcoded_secret_redacted():
    diff = """--- a/secret.py\n+++ b/secret.py\n@@ -5,0 +6,1 @@\n+API_KEY = \"12345-abcdef\"\n"""
    findings = await review_security(diff, MockProvider())
    secret = next(f for f in findings if f.severity == "critical")
    assert "Hard‑coded secret" in secret.description
    assert "[REDACTED]" in secret.evidence
    assert secret.line_number == 3

@pytest.mark.asyncio
async def test_unsafe_deserialization_finding():
    diff = """--- a/deserialize.py\n+++ b/deserialize.py\n@@ -2,0 +3,1 @@\n+data = pickle.loads(user_blob)\n"""
    findings = await review_security(diff, MockProvider())
    deser = next(f for f in findings if "deserialization" in f.description.lower())
    assert deser.severity == "high"
    assert deser.line_number == 3

@pytest.mark.asyncio
async def test_dangerous_file_write_finding():
    diff = """--- a/write.py\n+++ b/write.py\n@@ -1,0 +2,2 @@\n+with open('/tmp/evil.txt', 'w') as f:\n+    f.write(data)\n"""
    findings = await review_security(diff, MockProvider())
    file_write = next(f for f in findings if "unsafe file write" in f.description.lower())
    assert file_write.severity == "medium"
    assert file_write.line_number == 3

@pytest.mark.asyncio
async def test_safe_parameterized_sql_no_finding():
    diff = """--- a/safe.py\n+++ b/safe.py\n@@ -1,0 +1,1 @@\n+query = text(\"SELECT * FROM users WHERE id = :id\").bindparams(id=user_input)\n"""
    findings = await review_security(diff, MockProvider())
    assert not any(f.severity == "high" and "SQL injection" in f.description for f in findings)

@pytest.mark.asyncio
async def test_safe_code_no_finding():
    diff = """--- a/util.py\n+++ b/util.py\n@@ -1,0 +1,2 @@\n+def add(a, b):\n+    return a + b\n"""
    findings = await review_security(diff, MockProvider())
    assert findings == []

@pytest.mark.asyncio
async def test_malformed_provider_response():
    diff = """--- a/none.py\n+++ b/none.py\n@@ -1,0 +1,1 @@\n+print('hello')\n"""
    findings = await review_security(diff, MockProvider())
    assert findings == []

@pytest.mark.asyncio
async def test_provider_failure_handling():
    diff = """--- a/error.py\n+++ b/error.py\n@@ -1,0 +1,1 @@\n+MOCK_ERROR\n"""
    findings = await review_security(diff, MockProvider())
    assert findings == []

@pytest.mark.asyncio
async def test_invalid_line_numbers_and_empty_diff():
    findings = await review_security("", MockProvider())
    assert findings == []
    diff = """--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n- old line\n+ new line\n"""
    findings = await review_security(diff, MockProvider())
    assert isinstance(findings, list)
