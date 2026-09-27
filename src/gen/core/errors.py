"""Базовые исключения инструмента."""


class ContentGenError(Exception):
    """Базовое исключение для всех ошибок инструмента."""


class ProviderError(ContentGenError):
    """Ошибка вызова внешнего провайдера (LLM/изображения/видео/embedding)."""


class QCFailedError(ContentGenError):
    """Результат не прошёл контроль качества (сходство лица) после всех ретраев."""


class ComplianceError(ContentGenError):
    """Результат нарушает модерационные правила (нагота/несовершеннолетие/бренды)."""
