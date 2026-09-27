"""Мок ComplianceProvider для тестов (без сети)."""

from __future__ import annotations

from pathlib import Path

from gen.qc.compliance import ComplianceProvider, ComplianceResult


class MockComplianceProvider(ComplianceProvider):
    def __init__(self, *, passed: bool = True, reason: str | None = None) -> None:
        self._passed = passed
        self._reason = reason
        self.calls = 0

    def check(self, image: Path) -> ComplianceResult:
        self.calls += 1
        return ComplianceResult(passed=self._passed, reason=self._reason)
