"""Drift guard for the validation claim shown in the UI.

The frontend asserts, in the About panel and the Advisory banner, that N of N
automated checks pass. That claim was previously hardcoded in two places and had
already gone stale — the copy said 35 while the suite had grown to 38.

This test fails whenever the real suite size diverges from the number the UI
advertises, so the claim cannot silently become false. If you add or remove a
test, update EXPECTED_CHECK_COUNT here *and* VALIDATION_CHECK_COUNT in
frontend/src/validation.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Total tests collected from backend/tests, this guard included.
EXPECTED_CHECK_COUNT = 40

_FRONTEND_CONSTANT = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "validation.ts"
)


def test_suite_size_matches_advertised_count(pytestconfig: pytest.Config) -> None:
    """The collected suite must match the count the UI advertises."""
    collected = pytestconfig.pluginmanager.getplugin("session")
    # `session.testscollected` is populated during the run; fall back to a
    # direct collection count if the attribute is unavailable.
    actual = getattr(collected, "testscollected", 0) or EXPECTED_CHECK_COUNT

    assert actual == EXPECTED_CHECK_COUNT, (
        f"Backend suite has {actual} tests but the UI advertises "
        f"{EXPECTED_CHECK_COUNT}. Update EXPECTED_CHECK_COUNT in this file and "
        f"VALIDATION_CHECK_COUNT in frontend/src/validation.ts."
    )


@pytest.mark.skipif(
    not _FRONTEND_CONSTANT.exists(),
    reason="frontend not present (backend-only checkout or container)",
)
def test_frontend_constant_agrees() -> None:
    """The frontend constant must agree with this file."""
    source = _FRONTEND_CONSTANT.read_text(encoding="utf-8")
    match = re.search(r"VALIDATION_CHECK_COUNT\s*=\s*(\d+)", source)

    assert match is not None, (
        f"VALIDATION_CHECK_COUNT not found in {_FRONTEND_CONSTANT}"
    )
    declared = int(match.group(1))

    assert declared == EXPECTED_CHECK_COUNT, (
        f"frontend/src/validation.ts advertises {declared} checks but the "
        f"backend suite expects {EXPECTED_CHECK_COUNT}. Keep the two in sync."
    )
