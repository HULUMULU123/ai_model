"""Доставка результата в локальную папку `output/<timestamp>/`.

История генераций — просто файлы рядом с результатом (ТЗ §7), без БД:
итоговый медиафайл + `meta.json` с промптом, QC score и флагом low-confidence.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def deliver_to_output(
    candidate_path: Path,
    *,
    prompt: str,
    qc_score: float,
    low_confidence: bool,
    output_root: Path = Path("output"),
) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    run_dir = output_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    dest = run_dir / candidate_path.name
    shutil.copyfile(candidate_path, dest)

    meta = {
        "prompt": prompt,
        "qc_score": qc_score,
        "low_confidence": low_confidence,
        "source_file": candidate_path.name,
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return dest
