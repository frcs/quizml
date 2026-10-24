from types import SimpleNamespace

import pytest

from quizml.cli.sample import run_sample
from quizml.exceptions import QuizMLError
from quizml.yaml import load


def test_sample_preserves_figures_path_without_root_header(tmp_path):
    bank_dir = tmp_path / "bank"
    bank_dir.mkdir()
    (bank_dir / "questions.yaml").write_text(
        "- type: tf\n  question: Q1\n  answer: true\n",
        encoding="utf-8",
    )
    meta = tmp_path / "meta.yaml"
    meta.write_text("- _include: bank/questions.yaml\n", encoding="utf-8")
    out = tmp_path / "out.yaml"

    run_sample(SimpleNamespace(file=str(meta), output=str(out), seed="42", force=True))

    doc = load(str(out), validate=False)
    assert doc["paths"]["figure_dirs"] == ["bank"]
    assert "_figures_path: [bank]" in out.read_text(
        encoding="utf-8"
    ) or "- bank" in out.read_text(encoding="utf-8")


def test_sample_preserves_figure_directory_order(tmp_path):
    z_dir = tmp_path / "z_bank"
    a_dir = tmp_path / "a_bank"
    z_dir.mkdir()
    a_dir.mkdir()
    (z_dir / "q.yaml").write_text(
        "- type: tf\n  question: QZ\n  answer: true\n", encoding="utf-8"
    )
    (a_dir / "q.yaml").write_text(
        "- type: tf\n  question: QA\n  answer: true\n", encoding="utf-8"
    )
    meta = tmp_path / "meta.yaml"
    meta.write_text(
        "title: Ordered\n---\n- _include: z_bank/q.yaml\n- _include: a_bank/q.yaml\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.yaml"

    run_sample(SimpleNamespace(file=str(meta), output=str(out), seed="42", force=True))

    doc = load(str(out), validate=False)
    assert doc["paths"]["figure_dirs"] == ["z_bank", "a_bank"]


def test_sample_derives_distinct_seeds_across_multiple_includes(tmp_path):
    bank1 = tmp_path / "bank1.yaml"
    bank2 = tmp_path / "bank2.yaml"
    items_1 = "\n".join(
        f"- type: tf\n  question: B1_{i}\n  answer: true" for i in range(10)
    )
    items_2 = "\n".join(
        f"- type: tf\n  question: B2_{i}\n  answer: true" for i in range(10)
    )
    bank1.write_text(items_1 + "\n", encoding="utf-8")
    bank2.write_text(items_2 + "\n", encoding="utf-8")

    meta = tmp_path / "meta.yaml"
    meta.write_text(
        "- _include: bank1.yaml\n  count: 3\n- _include: bank2.yaml\n  count: 3\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.yaml"

    run_sample(
        SimpleNamespace(file=str(meta), output=str(out), seed="shared-seed", force=True)
    )

    doc = load(str(out), validate=False)
    qs = [q["question"] for q in doc["questions"]]
    b1_indices = [int(q.split("_")[1]) for q in qs[:3]]
    b2_indices = [int(q.split("_")[1]) for q in qs[3:]]
    assert b1_indices != b2_indices


def test_sample_rejects_count_exceeding_bank_size(tmp_path):
    bank = tmp_path / "bank.yaml"
    bank.write_text(
        "- type: tf\n  question: Q1\n  answer: true\n",
        encoding="utf-8",
    )
    meta = tmp_path / "meta.yaml"
    meta.write_text(
        "- _include: bank.yaml\n  count: 5\n  seed: 1\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.yaml"

    with pytest.raises(QuizMLError, match="exceeds available questions"):
        run_sample(
            SimpleNamespace(file=str(meta), output=str(out), seed=None, force=True)
        )


def test_sample_rejects_unknown_include_keys_and_unprefixed_include(tmp_path):
    bank = tmp_path / "bank.yaml"
    bank.write_text(
        "- type: tf\n  question: Q1\n  answer: true\n",
        encoding="utf-8",
    )
    meta_unknown = tmp_path / "meta_unknown.yaml"
    meta_unknown.write_text(
        "- _include: bank.yaml\n  couunt: 1\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.yaml"

    with pytest.raises(QuizMLError, match="Unknown key"):
        run_sample(
            SimpleNamespace(
                file=str(meta_unknown), output=str(out), seed="1", force=True
            )
        )

    meta_unprefixed = tmp_path / "meta_unprefixed.yaml"
    meta_unprefixed.write_text(
        "- include: bank.yaml\n",
        encoding="utf-8",
    )
    with pytest.raises(QuizMLError, match="Did you mean '_include'"):
        run_sample(
            SimpleNamespace(
                file=str(meta_unprefixed), output=str(out), seed="1", force=True
            )
        )
