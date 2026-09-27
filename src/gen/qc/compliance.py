"""Модерационная проверка (нагота/несовершеннолетие/чужие бренды).

TODO: не реализовано. Ни в RouterAI, ни в fal.ai нет проверенной здесь
документации на конкретный эндпоинт NSFW/age-модерации — сигнатура запроса
не подтверждена, поэтому адаптер не выдумывается (см. CLAUDE.md). Перед
реализацией свериться с документацией провайдера модерации (например,
OpenAI moderation API, если он доступен через тот же ключ, или отдельный
NSFW-классификатор). До тех пор реальный провайдер кидает
`NotImplementedError`; узел графа работает через `ComplianceProvider`
интерфейс и мок для тестов.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel


class ComplianceResult(BaseModel):
    passed: bool
    reason: str | None = None


class ComplianceProvider(ABC):
    @abstractmethod
    def check(self, image: Path) -> ComplianceResult:
        """Проверяет файл на нарушения (нагота/несовершеннолетие/чужие бренды)."""


class NotImplementedComplianceProvider(ComplianceProvider):
    def check(self, image: Path) -> ComplianceResult:
        raise NotImplementedError(
            "ComplianceProvider.check: модерационный эндпоинт не подтверждён "
            "документацией, см. TODO в шапке файла"
        )
