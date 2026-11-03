import os
import shutil

import platformdirs

from ..exceptions import QuizMLConfigError
from .errorhandler import err_console

BUNDLE_GROUPS = {
    "latex": [
        "tcd-exam.tex.j2",
        "tcd-exam-solutions.tex.j2",
        "math-preamble.tex",
        "omrglyphs.sty",
    ],
    "html": ["preview.html.j2", "markdown-html.css", "math-preamble.tex"],
    "bb": ["blackboard.txt.j2", "markdown-html.css", "math-preamble.tex"],
    "docx": ["tcd-exam.docx"],
    "qti": ["qti12", "qti21"],
    "moodle": ["moodle.xml.j2"],
    "schema": ["schema.json"],
}


def _select_files(
    *,
    all_files=False,
    latex=False,
    html=False,
    bb=False,
    docx=False,
    qti=False,
    moodle=False,
    schema=False,
    templates=None,
):
    if all_files:
        return None  # Indicates full directory copy
    selected = ["quizml.cfg"]
    if latex:
        selected.extend(BUNDLE_GROUPS["latex"])
    if html:
        selected.extend(BUNDLE_GROUPS["html"])
    if bb:
        selected.extend(BUNDLE_GROUPS["bb"])
    if docx:
        selected.extend(BUNDLE_GROUPS["docx"])
    if qti:
        selected.extend(BUNDLE_GROUPS["qti"])
    if moodle:
        selected.extend(BUNDLE_GROUPS["moodle"])
    if schema:
        selected.extend(BUNDLE_GROUPS["schema"])
    if templates:
        for t in templates:
            selected.append(t)
    # Deduplicate while preserving order
    return list(dict.fromkeys(selected))


def _copy_templates(dest_dir, files_to_copy=None, *, force=False):
    pkg_template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../templates")
    )
    if not os.path.isdir(pkg_template_dir):
        raise QuizMLConfigError(f"Template directory not found at {pkg_template_dir}")

    try:
        if files_to_copy is None:
            if os.path.exists(dest_dir) and not force:
                existing = [
                    f
                    for f in os.listdir(dest_dir)
                    if not f.endswith(".py") and f != "__pycache__"
                ]
                if existing:
                    raise QuizMLConfigError(
                        f"Destination '{dest_dir}' already contains files ({', '.join(sorted(existing))}). "
                        "Use --force to overwrite."
                    )
            shutil.copytree(
                pkg_template_dir,
                dest_dir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("*.py", "__pycache__", "*.pyc"),
            )
            err_console.print(
                f"Successfully copied all templates from {pkg_template_dir} to {dest_dir}"
            )
            return True

        os.makedirs(dest_dir, exist_ok=True)
        conflicts = []
        for filename in files_to_copy:
            src_path = os.path.join(pkg_template_dir, filename)
            if not (os.path.isfile(src_path) or os.path.isdir(src_path)):
                raise QuizMLConfigError(
                    f"Bundled template '{filename}' not found in {pkg_template_dir}"
                )
            dst_path = os.path.join(dest_dir, filename)
            if os.path.exists(dst_path) and not force:
                conflicts.append(filename)

        if conflicts:
            raise QuizMLConfigError(
                f"File(s) already exist in '{dest_dir}': {', '.join(conflicts)}. "
                "Use --force to overwrite."
            )

        for filename in files_to_copy:
            src_path = os.path.join(pkg_template_dir, filename)
            dst_path = os.path.join(dest_dir, filename)
            if os.path.isdir(src_path):
                shutil.copytree(
                    src_path,
                    dst_path,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.py", "__pycache__", "*.pyc"),
                )
            else:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

        err_console.print(f"Initialized {', '.join(files_to_copy)} in {dest_dir}")
        return True
    except OSError as e:
        raise QuizMLConfigError(f"Could not copy templates to {dest_dir}: {e}") from e


def _update_existing_templates(dest_dir, extra_templates=None):
    pkg_template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../templates")
    )
    if not os.path.isdir(pkg_template_dir):
        raise QuizMLConfigError(f"Template directory not found at {pkg_template_dir}")

    if not os.path.isdir(dest_dir):
        err_console.print(f"No existing template directory at {dest_dir}")
        return True

    bundled_entries = [
        f
        for f in sorted(os.listdir(pkg_template_dir))
        if not f.endswith((".py", ".pyc")) and f != "__pycache__"
    ]
    explicit = set(extra_templates or [])
    to_update = [
        f
        for f in bundled_entries
        if (f != "quizml.cfg" or f in explicit)
        and os.path.exists(os.path.join(dest_dir, f))
    ]

    if not to_update:
        err_console.print(f"No bundled templates found in {dest_dir} to update.")
        return True

    try:
        for filename in to_update:
            src_path = os.path.join(pkg_template_dir, filename)
            dst_path = os.path.join(dest_dir, filename)
            if os.path.isdir(src_path):
                shutil.copytree(
                    src_path,
                    dst_path,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.py", "__pycache__", "*.pyc"),
                )
            else:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
        err_console.print(f"Updated {', '.join(to_update)} in {dest_dir}")
        return True
    except OSError as e:
        raise QuizMLConfigError(f"Could not update templates in {dest_dir}: {e}") from e


def init_local(
    *,
    all_files=False,
    latex=False,
    html=False,
    bb=False,
    docx=False,
    qti=False,
    moodle=False,
    schema=False,
    templates=None,
    force=False,
    update=False,
):
    local_template_dir = os.path.join(os.getcwd(), "_quizml")
    if update:
        return _update_existing_templates(local_template_dir, extra_templates=templates)
    files_to_copy = _select_files(
        all_files=all_files,
        latex=latex,
        html=html,
        bb=bb,
        docx=docx,
        qti=qti,
        moodle=moodle,
        schema=schema,
        templates=templates,
    )
    return _copy_templates(local_template_dir, files_to_copy, force=force)


def init_user(
    *,
    all_files=False,
    latex=False,
    html=False,
    bb=False,
    docx=False,
    qti=False,
    moodle=False,
    schema=False,
    templates=None,
    force=False,
    update=False,
):
    app_dir = platformdirs.user_config_dir(appname="quizml", appauthor="frcs")
    user_template_dir = os.path.join(app_dir, "templates")
    if update:
        return _update_existing_templates(user_template_dir, extra_templates=templates)
    files_to_copy = _select_files(
        all_files=all_files,
        latex=latex,
        html=html,
        bb=bb,
        docx=docx,
        qti=qti,
        moodle=moodle,
        schema=schema,
        templates=templates,
    )
    return _copy_templates(user_template_dir, files_to_copy, force=force)
