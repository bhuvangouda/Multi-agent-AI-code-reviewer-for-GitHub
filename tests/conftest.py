import sys
import asyncio
import pytest

@pytest.fixture(scope="session")
def event_loop_policy():
    """Provide a Windows‑compatible event loop policy for async tests.

    pytest‑asyncio will use this policy when creating its internal ``event_loop``
    fixture. On non‑Windows platforms the default policy is returned.
    """
    if sys.platform.startswith("win"):
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()
