"""Companion utility to clean up generated targets and LaTeX compilation artifacts."""

from pathlib import Path

# Suffixes relative to the YAML base stem (e.g. "exam" -> "exam" + suffix)
KNOWN_TARGET_SUFFIXES = {
    ".txt",
    ".html",
    ".tex",
    ".solutions.tex",
    ".pdf",
    ".solutions.pdf",
    ".docx",
    ".csv",
}

# Intermediate LaTeX build artifact extensions
LATEX_ARTIFACT_EXTENSIONS = {
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
}


def get_cleanup_candidates(stem: str) -> set[str]:
    """Returns the set of filenames that are known build artifacts or targets for a given YAML stem."""
    candidates = {f"{stem}{s}" for s in KNOWN_TARGET_SUFFIXES}
    for base in (stem, f"{stem}.solutions"):
        for ext in LATEX_ARTIFACT_EXTENSIONS:
            candidates.add(f"{base}{ext}")
    return candidates


def find_cleanup_files(
    directory_path: str | Path = ".",
    target_stems: list[str] | None = None,
) -> list[Path]:
    """Finds all generated targets and LaTeX artifacts matching YAML files in directory_path."""
    dir_path = Path(directory_path).resolve()
    if not dir_path.is_dir():
        return []

    if target_stems:
        stems = [s.removesuffix(".yaml").removesuffix(".yml") for s in target_stems]
    else:
        stems = [
            f.stem
            for f in dir_path.iterdir()
            if f.is_file() and f.suffix in (".yaml", ".yml")
        ]

    matched_files = []
    for stem in stems:
        candidates = get_cleanup_candidates(stem)
        for candidate_name in candidates:
            candidate_path = dir_path / candidate_name
            if candidate_path.is_file():
                matched_files.append(candidate_path)

    return sorted(matched_files)


def cleanup_build(
    directory_path: str | Path = ".",
    dry_run: bool = False,
    target_stems: list[str] | None = None,
) -> list[Path]:
    """Cleans up generated build artifacts.

    Returns the list of cleaned (or dry-run candidate) file paths.
    """
    files = find_cleanup_files(directory_path, target_stems=target_stems)
    if not dry_run:
        for f in files:
            try:
                f.unlink()
            except OSError:
                pass
    return files
