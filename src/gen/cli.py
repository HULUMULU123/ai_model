"""Точки входа CLI: init-persona и generate.

generate: каркас команды, реальная логика графа появится на этапах M3-M5.
"""

from __future__ import annotations

from pathlib import Path

import click

DEFAULT_PERSONA_DIR = Path("persona")


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
    from gen.graph.init_persona.run import run_init_persona

    if not name:
        raise click.UsageError("--name обязателен")

    brief_text = ""
    if brief:
        brief_path = Path(brief)
        brief_text = brief_path.read_text(encoding="utf-8") if brief_path.is_file() else brief

    result = run_init_persona(
        brief=brief_text,
        name=name,
        persona_dir=DEFAULT_PERSONA_DIR,
        variants=variants,
        full_reference_set=full_reference_set,
    )

    click.echo(f"Готово: {DEFAULT_PERSONA_DIR}/bible.md, persona.yaml, wardrobe.yaml")
    click.echo(f"Референсы: {len(result['canon_images'])} файлов в {DEFAULT_PERSONA_DIR}/canon/")
    if result.get("qc_warning"):
        click.echo(f"QC предупреждение: {result['qc_warning']}")


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
