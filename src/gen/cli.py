"""Точки входа CLI: init-persona и generate.

M0: только каркас команд и их опций. Реальная логика графов (init_persona,
generate) появится на этапах M2-M5.
"""

from __future__ import annotations

import click


@click.command()
@click.option("--brief", type=click.Path(exists=False), default=None, help="Файл с брифом персонажа.")
@click.option("--name", type=str, default=None, help="Имя персонажа.")
@click.option(
    "--full-reference-set",
    is_flag=True,
    default=False,
    help="Сгенерировать расширенный набор референсов (не по умолчанию, дороже).",
)
@click.option(
    "--variants",
    type=int,
    default=1,
    show_default=True,
    help="Число кандидатов на кадр эталонного набора.",
)
def init_persona(brief: str | None, name: str | None, full_reference_set: bool, variants: int) -> None:
    """Подготовить характер и эталонную внешность персонажа за один проход."""
    raise NotImplementedError("init-persona: граф init_persona будет реализован на этапе M2")


@click.command()
@click.option("--brief", type=str, required=True, help="Бриф на конкретный кадр (сцена/действие).")
@click.option(
    "--format",
    "format_",
    type=click.Choice(["photo", "video"]),
    default="photo",
    show_default=True,
    help="Тип генерируемого контента.",
)
@click.option("--n", type=int, default=1, show_default=True, help="Число генераций на бриф.")
@click.option(
    "--retries",
    type=int,
    default=1,
    show_default=True,
    help="Максимум повторов при провале QC.",
)
def generate(brief: str, format_: str, n: int, retries: int) -> None:
    """Сгенерировать фото или видео персонажа по брифу на кадр."""
    raise NotImplementedError("generate: граф generate будет реализован на этапах M3-M5")


if __name__ == "__main__":
    init_persona()
