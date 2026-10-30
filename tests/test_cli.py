import sys
from unittest.mock import patch

import pytest

from quizml.cli.cli import main


@patch("quizml.cli.ui.print_target_list")
def test_target_list(mock_print_target_list):
    with patch.object(sys, "argv", ["quizml", "targets"]):
        main()
    mock_print_target_list.assert_called_once()


@patch("quizml.cli.cleanup.cleanup_yaml_files")
@patch("quizml.cli.config.get_config", return_value={"targets": []})
def test_cleanup(mock_get_config, mock_cleanup):
    with patch.object(sys, "argv", ["quizml", "clean", "--config", "quizml.cfg"]):
        main()
    assert mock_get_config.call_args.args[0].config == "quizml.cfg"
    mock_cleanup.assert_called_once()


def test_cleanup_safety(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    # Create exam yaml
    exam_yaml = tmp_path / "exam.yaml"
    exam_yaml.write_text("title: Test\n---\n[]")

    # Target outputs and artifacts that SHOULD be cleaned up
    targets_to_clean = [
        tmp_path / "exam.txt",
        tmp_path / "exam.html",
        tmp_path / "exam.tex",
        tmp_path / "exam.solutions.tex",
        tmp_path / "exam.pdf",
        tmp_path / "exam.solutions.pdf",
        tmp_path / "exam.aux",
        tmp_path / "exam.solutions.aux",
        tmp_path / "exam.log",
        tmp_path / "exam.synctex.gz",
        tmp_path / "exam.docx",
    ]
    for p in targets_to_clean:
        p.write_text("generated artifact")

    # Non-target files that MUST NOT be cleaned up
    safe_files = [
        tmp_path / "exam.py",
        tmp_path / "exam.md",
        tmp_path / "exam.png",
        tmp_path / "other_notes.txt",
        exam_yaml,
    ]
    for p in safe_files:
        if not p.exists():
            p.write_text("precious authored file")

    latex_sidecars = [
        ".aux",
        ".log",
        ".out",
        ".fls",
        ".fdb_latexmk",
        ".synctex.gz",
        ".toc",
        ".nav",
        ".snm",
        ".vrb",
        ".bbl",
        ".blg",
        ".dvi",
        ".xdv",
    ]
    targets = [
        {"out": "${inputbasename}.txt"},
        {"out": "${inputbasename}.html"},
        {
            "out": "${inputbasename}.tex",
        },
        {"out": "${inputbasename}.solutions.tex"},
        {"out": "${inputbasename}.pdf", "clean_extensions": latex_sidecars},
        {
            "out": "${inputbasename}.solutions.pdf",
            "clean_extensions": latex_sidecars,
        },
        {"out": "${inputbasename}.docx"},
    ]
    deleted_count = cleanup_yaml_files(str(tmp_path), targets=targets)

    # Verify all targets/artifacts were deleted
    assert deleted_count == len(targets_to_clean)
    for p in targets_to_clean:
        assert not p.exists(), f"Expected {p.name} to be deleted"

    # Verify all safe files are untouched
    for p in safe_files:
        assert p.exists(), f"Expected {p.name} to be preserved"


def test_cleanup_specific_target_stem(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    # Create two exams and their artifacts
    (tmp_path / "exam1.html").write_text("artifact")
    (tmp_path / "exam2.html").write_text("artifact")

    # Only clean exam1
    deleted_count = cleanup_yaml_files(
        str(tmp_path), target_stems={"exam1"}, targets=[{"out": "${inputstem}.html"}]
    )

    assert deleted_count == 1
    assert not (tmp_path / "exam1.html").exists()
    assert (tmp_path / "exam2.html").exists()


def test_cleanup_custom_nested_output_and_sidecar(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    (tmp_path / "exam.yaml").write_text("---\n[]")
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    (output_dir / "exam.quizpack").write_text("output")
    (output_dir / "exam.manifest").write_text("sidecar")
    (output_dir / "unrelated.txt").write_text("keep")

    deleted_count = cleanup_yaml_files(
        str(tmp_path),
        targets=[
            {
                "out": "artifacts/${inputbasename}.quizpack",
                "clean_extensions": [".manifest"],
            }
        ],
    )

    assert deleted_count == 2
    assert not (output_dir / "exam.quizpack").exists()
    assert not (output_dir / "exam.manifest").exists()
    assert (output_dir / "unrelated.txt").exists()


def test_cleanup_absolute_output_path(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    quiz_dir = tmp_path / "quizzes"
    quiz_dir.mkdir()
    (quiz_dir / "exam.yaml").write_text("---\n[]")
    output = tmp_path / "published" / "exam.output"
    output.parent.mkdir()
    output.write_text("output")

    deleted_count = cleanup_yaml_files(str(quiz_dir), targets=[{"out": str(output)}])

    assert deleted_count == 1
    assert not output.exists()


def test_cleanup_never_deletes_yaml_sources(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    source = tmp_path / "exam.yaml"
    source.write_text("---\n[]")

    deleted_count = cleanup_yaml_files(
        str(tmp_path), targets=[{"out": "${inputbasename}.yaml"}]
    )

    assert deleted_count == 0
    assert source.exists()


def test_cleanup_dry_run_preserves_configured_outputs(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    (tmp_path / "exam.yaml").write_text("---\n[]")
    output = tmp_path / "exam.custom"
    output.write_text("output")

    with patch("quizml.cli.cleanup.err_console.print") as mock_print:
        deleted_count = cleanup_yaml_files(
            str(tmp_path), dry_run=True, targets=[{"out": "${inputbasename}.custom"}]
        )

    assert deleted_count == 0
    assert output.exists()
    assert any("exam.custom" in str(call) for call in mock_print.call_args_list)


def test_cleanup_rejects_path_like_clean_extensions(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files
    from quizml.exceptions import QuizMLConfigError

    (tmp_path / "exam.yaml").write_text("---\n[]")

    with pytest.raises(QuizMLConfigError, match="clean_extensions"):
        cleanup_yaml_files(
            str(tmp_path),
            targets=[
                {
                    "out": "${inputbasename}.pdf",
                    "clean_extensions": ["../important.txt"],
                }
            ],
        )


@patch("quizml.cli.init.init_local")
def test_init_local(mock_init_local):
    with patch.object(sys, "argv", ["quizml", "init", "local"]):
        main()
    mock_init_local.assert_called_once()


@patch("quizml.cli.init.init_user")
def test_init_user(mock_init_user):
    with patch.object(sys, "argv", ["quizml", "init", "user"]):
        main()
    mock_init_user.assert_called_once()


@patch("sys.stdout.write")
def test_shell_completion(mock_write):
    with patch.object(sys, "argv", ["quizml", "completion", "bash"]):
        main()
    mock_write.assert_called()


def test_missing_yaml_file(capsys):
    with patch.object(sys, "argv", ["quizml"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2  # argparse error code


@patch("quizml.cli.compile.compile")
def test_compile_default(mock_compile):
    with patch.object(sys, "argv", ["quizml", "test.yaml"]):
        main()
    mock_compile.assert_called_once()


@patch("quizml.cli.diff.diff")
def test_diff_command(mock_diff):
    with patch.object(sys, "argv", ["quizml", "diff", "test1.yaml", "test2.yaml"]):
        main()
    mock_diff.assert_called_once()


def test_diff_execution(tmp_path, capsys):
    f1 = tmp_path / "quiz1.yaml"
    f2 = tmp_path / "quiz2.yaml"
    content = """
- type: tf
  marks: 2.5
  question: Is this a test question?
  answer: true
"""
    f1.write_text(content)
    f2.write_text(content)

    with patch.object(sys, "argv", ["quizml", "diff", str(f1), str(f2)]):
        main()

    captured = capsys.readouterr()
    assert "Is this a test question?" in captured.out
    assert "tf" in captured.out


def test_version(capsys):
    with patch.object(sys, "argv", ["quizml", "--version"]):
        with pytest.raises(SystemExit):
            main()
    # verify output contains version? argparse usually prints to stdout/stderr


def test_info_command(capsys):
    import json

    with patch.object(sys, "argv", ["quizml", "info"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    output = captured.out

    # Check if output is valid JSON
    data = json.loads(output)

    expected_keys = [
        "version",
        "cwd",
        "local_templates",
        "user_config_dir",
        "user_templates",
        "package_templates",
        "search_paths",
        "config_file",
        "cache_dir",
        "cache_size_bytes",
    ]

    for key in expected_keys:
        assert key in data


def test_cache_clear_command(capsys):
    with (
        patch.object(sys, "argv", ["quizml", "cache", "clear"]),
        patch("quizml.cache.clear_cache", return_value=123),
    ):
        main()

    captured = capsys.readouterr()
    assert "Cleared 123 bytes from QuizML cache" in captured.err
    assert captured.out == ""


def test_compile_failure_exit_code_and_stderr(tmp_path, capsys):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("- type: tf\n  question: test\n  answer: maybe\n")

    with patch.object(sys, "argv", ["quizml", str(bad_yaml)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Schema validation error" in captured.err
    assert captured.err.count("Schema validation error") == 1
    assert captured.out == ""


def test_compile_missing_file_exit_code_and_stderr(capsys):
    with patch.object(sys, "argv", ["quizml", "does_not_exist_98765.yaml"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Error" in captured.err or len(captured.err) > 0
    assert captured.out == ""


def test_cleanup_missing_dir_exit_code():
    with patch.object(sys, "argv", ["quizml", "clean", "does_not_exist_dir_98765"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_diff_missing_file_exit_code():
    with patch.object(
        sys, "argv", ["quizml", "diff", "f1_missing.yaml", "f2_missing.yaml"]
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_target_list_config_failure_exit_code_and_stderr(capsys):
    from quizml.exceptions import QuizMLConfigError

    with patch.object(sys, "argv", ["quizml", "targets"]):
        with patch(
            "quizml.cli.ui.get_config", side_effect=QuizMLConfigError("bad config")
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "bad config" in captured.err
    assert captured.out == ""


def test_init_copy_failure_exit_code_and_stderr(tmp_path, monkeypatch, capsys):
    import quizml.cli.init as init_module

    monkeypatch.chdir(tmp_path)
    with patch.object(
        init_module.shutil, "copy2", side_effect=OSError("permission denied")
    ):
        with patch.object(sys, "argv", ["quizml", "init", "local"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "permission denied" in captured.err
    assert captured.out == ""


def test_diff_check_exits_nonzero_on_duplicates(tmp_path, capsys):
    f1 = tmp_path / "q1.yaml"
    f2 = tmp_path / "q2.yaml"
    content = "- type: tf\n  question: Same question?\n  answer: true\n"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    with patch.object(
        sys, "argv", ["quizml", "diff", "--check", "--quiet", str(f1), str(f2)]
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert captured.out == ""


def test_clean_quiet_suppresses_stderr(tmp_path, capsys):
    from quizml.cli.cleanup import cleanup_yaml_files

    (tmp_path / "exam.yaml").write_text("---\n[]", encoding="utf-8")
    (tmp_path / "exam.html").write_text("artifact", encoding="utf-8")

    deleted = cleanup_yaml_files(
        str(tmp_path), targets=[{"out": "${inputbasename}.html"}], quiet=True
    )
    assert deleted == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_sample_stdin_to_stdout(tmp_path, monkeypatch, capsys):
    import io

    bank = tmp_path / "bank.yaml"
    bank.write_text(
        "- type: tf\n  question: Sampled from bank?\n  answer: true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "stdin", io.StringIO("- _include: bank.yaml\n  count: 1\n")
    )

    with patch.object(sys, "argv", ["quizml", "sample", "--seed", "1"]):
        main()

    captured = capsys.readouterr()
    assert "Sampled from bank?" in captured.out
    assert captured.err == ""


def test_compile_stdin_to_stdout(tmp_path, monkeypatch, capsys):
    import io

    cfg = tmp_path / "quizml.cfg"
    cfg.write_text(
        """
schema_path: schema.json
targets:
  - name: bb
    template: blackboard.txt.j2
    out: "-"
    markdown:
      format: html
      math: svg
      html_postprocess: blackboard_html
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("- type: tf\n  question: Piped question?\n  answer: true\n"),
    )

    with patch.object(
        sys, "argv", ["quizml", "compile", "--quiet", "--config", str(cfg), "-"]
    ):
        main()

    captured = capsys.readouterr()
    assert "TF\t<p>Piped question?</p>\tTrue" in captured.out


def test_init_excludes_python_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch.object(sys, "argv", ["quizml", "init", "local", "--all"]):
        main()

    dest_dir = tmp_path / "_quizml"
    assert dest_dir.exists()
    assert not (dest_dir / "__init__.py").exists()
    assert not (dest_dir / "__pycache__").exists()
    assert (dest_dir / "preview.html.j2").exists()


def test_init_tiered_default_and_selective_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Default init only creates _quizml/quizml.cfg
    with patch.object(sys, "argv", ["quizml", "init"]):
        main()

    dest_dir = tmp_path / "_quizml"
    assert (dest_dir / "quizml.cfg").exists()
    assert not (dest_dir / "schema.json").exists()
    assert not (dest_dir / "tcd-exam.tex.j2").exists()

    # Re-running without --force raises error (exits 1)
    with patch.object(sys, "argv", ["quizml", "init"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    # Selective --latex --schema --qti --moodle with --force succeeds
    with patch.object(
        sys,
        "argv",
        ["quizml", "init", "--latex", "--schema", "--qti", "--moodle", "--force"],
    ):
        main()

    assert (dest_dir / "schema.json").exists()
    assert (dest_dir / "tcd-exam.tex.j2").exists()
    assert (dest_dir / "math-preamble.tex").exists()
    assert (dest_dir / "omrglyphs.sty").exists()
    assert (dest_dir / "qti12" / "quiz.xml.j2").exists()
    assert (dest_dir / "qti21" / "item.xml.j2").exists()
    assert (dest_dir / "moodle.xml.j2").exists()
    assert not (dest_dir / "preview.html.j2").exists()


def test_targets_non_tty_tab_separated(capsys):
    with patch.object(sys, "argv", ["quizml", "targets"]):
        with patch.object(sys.stdout, "isatty", return_value=False):
            main()

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().splitlines() if line]
    assert len(lines) >= 1
    assert "\t" in lines[0]
    assert "┏" not in captured.out


def test_diff_non_tty_tab_separated(tmp_path, capsys):
    f1 = tmp_path / "q1.yaml"
    f2 = tmp_path / "q2.yaml"
    content = "- type: tf\n  question: Duplicate question?\n  answer: true\n"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    with patch.object(sys, "argv", ["quizml", "diff", str(f1), str(f2)]):
        with patch.object(sys.stdout, "isatty", return_value=False):
            main()

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().splitlines() if line]
    assert len(lines) == 1
    assert lines[0].startswith("1\ttf\tDuplicate question?\t")
    assert "┏" not in captured.out


def test_pin_stamps_metadata_adds_ids_and_freezes_includes(tmp_path):
    from quizml.yaml import load

    bank = tmp_path / "bank.yaml"
    bank.write_text(
        """
- title: Gradient Descent
  type: essay
  marks: 5
  question: Explain stochastic gradient descent.
""",
        encoding="utf-8",
    )

    exam = tmp_path / "exam.yaml"
    exam.write_text(
        """
- type: tf
  marks: 2
  question: Is ReLU linear?
  answer: false
- _include: bank.yaml
""",
        encoding="utf-8",
    )

    with patch.object(
        sys,
        "argv",
        [
            "quizml",
            "pin",
            str(exam),
            "-t",
            "pdf",
            "--add-ids",
            "--freeze-includes",
            "--quiet",
        ],
    ):
        main()

    doc = load(str(exam), validate=True)
    assert "_quizml" in doc["header"]
    assert doc["header"]["_targets"] == ["pdf"]
    assert len(doc["questions"]) == 2
    assert doc["questions"][0]["id"].startswith("is-relu-linear-")
    assert doc["questions"][1]["id"].startswith("gradient-descent-")


def test_diff_detects_matching_id_and_modified_distractor(tmp_path, capsys):
    f1 = tmp_path / "exam_2025.yaml"
    f2 = tmp_path / "exam_2026.yaml"
    f1.write_text(
        """
- type: mc
  question: Which activation function mitigates vanishing gradients best?
  choices:
    - x: ReLU
    - o: Sigmoid
    - o: Step function
    - o: Cosine
- id: q-backprop-1
  type: essay
  question: Derive the chain rule for a 2-layer MLP.
""",
        encoding="utf-8",
    )
    f2.write_text(
        """
- type: mc
  question: Which activation function mitigates vanishing gradients best?
  choices:
    - x: ReLU
    - o: Sigmoid
    - o: Step function
    - o: Hyperbolic tangent
- id: q-backprop-1
  type: essay
  question: Completely reworded backpropagation derivation question.
""",
        encoding="utf-8",
    )

    with patch.object(sys, "argv", ["quizml", "diff", str(f1), str(f2)]):
        with patch.object(sys.stdout, "isatty", return_value=False):
            main()

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().splitlines() if line]
    assert len(lines) == 2


def test_clean_recursive_and_header_variable_substitution(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    sub = tmp_path / "2025-2026" / "midterm"
    sub.mkdir(parents=True)
    quiz = sub / "paper.yaml"
    quiz.write_text(
        "modulecode: 4C16\n---\n- type: essay\n  question: Q1\n",
        encoding="utf-8",
    )
    artifact = sub / "4C16-paper.pdf"
    artifact.write_text("pdf", encoding="utf-8")

    # Non-recursive from root does not touch nested directory
    assert (
        cleanup_yaml_files(
            str(tmp_path),
            targets=[{"out": "${modulecode}-${inputstem}.pdf"}],
            quiet=True,
            recursive=False,
        )
        == 0
    )
    assert artifact.exists()

    # Recursive from root cleans nested directory and expands ${modulecode}
    assert (
        cleanup_yaml_files(
            str(tmp_path),
            targets=[{"out": "${modulecode}-${inputstem}.pdf"}],
            quiet=True,
            recursive=True,
        )
        == 1
    )
    assert not artifact.exists()


def test_mistyped_subcommand_exits_with_argparse_error():
    with patch.object(sys, "argv", ["quizml", "unknown_subcommand_xyz"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2


def test_build_alias_and_compile_output_override(tmp_path, monkeypatch, capsys):
    import io

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("- type: tf\n  question: Output override?\n  answer: true\n"),
    )

    with patch.object(
        sys, "argv", ["quizml", "build", "-", "-t", "bb", "-o", "-", "--quiet"]
    ):
        main()

    captured = capsys.readouterr()
    assert "TF\t<p>Output override?</p>\tTrue" in captured.out

