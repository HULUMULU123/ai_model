from pathlib import Path

import pytest

from gen.qc.compliance import NotImplementedComplianceProvider
from gen.qc.compliance_mock import MockComplianceProvider


def test_mock_compliance_passes():
    provider = MockComplianceProvider(passed=True)

    result = provider.check(Path("fake.png"))

    assert result.passed is True
    assert provider.calls == 1


def test_mock_compliance_rejects_with_reason():
    provider = MockComplianceProvider(passed=False, reason="nudity detected")

    result = provider.check(Path("fake.png"))

    assert result.passed is False
    assert result.reason == "nudity detected"


def test_real_compliance_provider_is_not_implemented():
    provider = NotImplementedComplianceProvider()

    with pytest.raises(NotImplementedError):
        provider.check(Path("fake.png"))
