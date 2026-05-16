"""Smoke orchestrator — runs both Humira (entity axis) + NASH (landscape axis)
golden tests in one pytest invocation.

Used in the CI deployment gate per ADR-0008:
    pytest tests/test_golden.py

Must pass for deployment. Individual xfails per subtest are allowed until
their target Phase lands; silent XPASS fails the suite (strict=True per
test case in test_humira_golden.py).
"""

from tests.test_humira_golden import *  # noqa: F401, F403
from tests.test_nash_landscape import *  # noqa: F401, F403
