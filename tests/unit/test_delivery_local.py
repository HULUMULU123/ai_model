import json

from gen.delivery.local import deliver_to_output


def test_deliver_to_output_copies_file_and_writes_meta(tmp_path):
    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(b"fake-image-bytes")
    output_root = tmp_path / "output"

    dest = deliver_to_output(
        candidate,
        prompt="сцена в кафе",
        qc_score=0.87,
        low_confidence=False,
        output_root=output_root,
    )

    assert dest.is_file()
    assert dest.read_bytes() == b"fake-image-bytes"
    assert dest.parent.parent == output_root

    meta = json.loads((dest.parent / "meta.json").read_text(encoding="utf-8"))
    assert meta["prompt"] == "сцена в кафе"
    assert meta["qc_score"] == 0.87
    assert meta["low_confidence"] is False


def test_deliver_to_output_creates_distinct_run_dirs(tmp_path):
    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(b"x")
    output_root = tmp_path / "output"

    dest1 = deliver_to_output(
        candidate, prompt="a", qc_score=0.5, low_confidence=False, output_root=output_root
    )
    dest2 = deliver_to_output(
        candidate, prompt="b", qc_score=0.6, low_confidence=False, output_root=output_root
    )

    assert dest1.parent != dest2.parent
