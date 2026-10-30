"""Subprocess runners for LaTeX, Ghostscript, and dvisvgm equation compilation."""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..exceptions import (
    DvisvgmNotFoundError,
    GhostscriptNotFoundError,
    LatexCompilationError,
    LatexNotFoundError,
    LatexToolError,
)


def build_tex_env(
    search_dirs: Iterable[str | Path] | None = None,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build an environment dict with ``search_dirs`` prepended to ``TEXINPUTS``."""
    env = dict(base_env if base_env is not None else os.environ)
    if not search_dirs:
        return env
    clean_dirs: list[str] = []
    for d in search_dirs:
        if d:
            abs_d = os.path.abspath(str(d))
            if abs_d not in clean_dirs:
                clean_dirs.append(abs_d)
    if not clean_dirs:
        return env
    existing = env.get("TEXINPUTS", "")
    prefix = os.pathsep.join(clean_dirs)
    if existing:
        if not existing.endswith(os.pathsep):
            existing = f"{existing}{os.pathsep}"
        env["TEXINPUTS"] = f"{prefix}{os.pathsep}{existing}"
    else:
        # Trailing os.pathsep ensures kpathsea still searches standard TEXMF trees.
        env["TEXINPUTS"] = f"{prefix}{os.pathsep}"
    return env


def _trim_tool_log(*outputs: str | None) -> str:
    """Extract the most relevant error tail (up to 40 lines) from TeX tool output."""
    lines = [line for output in outputs if output for line in output.splitlines()]
    error_index = next(
        (i for i, line in enumerate(lines) if line.startswith("!")), None
    )
    if error_index is not None:
        lines = lines[error_index:]
    return "\n".join(lines[-40:])


def _process_failure(
    tool_name: str, returncode: int, stdout: str | None, stderr: str | None
) -> LatexCompilationError:
    """Build a ``LatexCompilationError`` with trimmed diagnostic output."""
    details = _trim_tool_log(stdout, stderr) or "No diagnostic output was produced."
    return LatexCompilationError(
        f"{tool_name} failed with return code {returncode}\n{details}"
    )


def _launch_failure(
    tool_name: str,
    err: OSError,
    missing_error_cls: type[LatexToolError] = LatexNotFoundError,
) -> LatexToolError:
    """Translate an ``OSError`` from launching a tool into a ``LatexToolError``."""
    if isinstance(err, FileNotFoundError):
        return missing_error_cls(f"{tool_name} was not found while starting it.")
    detail = err.strerror or str(err)
    return LatexToolError(f"Could not start {tool_name}: {detail}")


def _communicate(process: subprocess.Popen[str], tool_name: str) -> tuple[str, str]:
    """Collect ``(stdout, stderr)`` from ``process``, wrapping OS errors."""
    try:
        return process.communicate()
    except OSError as err:
        detail = err.strerror or str(err)
        raise LatexToolError(
            f"Could not collect output from {tool_name}: {detail}"
        ) from err


class LatexRunner:
    """Context manager running ``pdflatex``, ``latex``, ``gs``, and ``dvisvgm``."""

    def __init__(
        self,
        working_dir_prefix: str = "quizml_latex_",
        tools: Mapping[str, str] | None = None,
        tex_search_dirs: Iterable[str | Path] | None = None,
    ) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix=working_dir_prefix))
        self.tools: dict[str, str] = dict(tools or {})
        self.tex_search_dirs: list[str | Path] = list(tex_search_dirs or [])

    def _tex_env(self) -> dict[str, str] | None:
        return build_tex_env(self.tex_search_dirs) if self.tex_search_dirs else None

    def _tool_cmd(self, key: str, default: str) -> str:
        return self.tools.get(key, default)

    @staticmethod
    def _require_executable(
        name: str, error_cls: type[LatexToolError], desc: str | None = None
    ) -> None:
        if not shutil.which(name):
            desc = desc or name
            raise error_cls(f"{desc} not found in PATH.")

    @staticmethod
    def _run_checked(
        command: list[str],
        tool_name: str,
        cwd: Path,
        missing_error_cls: type[LatexToolError] = LatexNotFoundError,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        run_kwargs: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "cwd": cwd,
            "check": False,
        }
        if env is not None:
            run_kwargs["env"] = env
        try:
            process = subprocess.run(command, **run_kwargs)
        except OSError as err:
            raise _launch_failure(tool_name, err, missing_error_cls) from err
        if process.returncode:
            raise _process_failure(
                tool_name, process.returncode, process.stdout, process.stderr
            )
        return process

    def _run_tex_engine(self, exe: str, latex_filename: Path) -> str:
        """Execute a TeX engine (``pdflatex`` or ``latex``) and return ``stdout``."""
        self._require_executable(exe, LatexNotFoundError)
        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "universal_newlines": True,
            "cwd": self.temp_dir,
        }
        tex_env = self._tex_env()
        if tex_env is not None:
            popen_kwargs["env"] = tex_env

        try:
            process = subprocess.Popen(
                [exe, "-interaction=nonstopmode", str(latex_filename)],
                **popen_kwargs,
            )
        except OSError as err:
            raise _launch_failure(exe, err) from err

        stdout, stderr = _communicate(process, exe)
        if process.returncode != 0:
            raise _process_failure(exe, process.returncode, stdout, stderr)
        return stdout

    def run_pdflatex(self, latex_content: str) -> tuple[Path, list[float]]:
        """Compile ``latex_content`` with ``pdflatex`` and parse depth ratios."""
        exe = self._tool_cmd("pdflatex", "pdflatex")
        latex_filename = self.temp_dir / "eq_list.tex"
        pdf_filename = self.temp_dir / "eq_list.pdf"
        latex_filename.write_text(latex_content, encoding="utf-8")

        stdout = self._run_tex_engine(exe, latex_filename)

        # Parse inline equation depth ratios (emitted via \typeout{::: ...}) and
        # check for any '!' TeX error lines in stdout.
        depthratio: list[float] = []
        err_msg = ""
        found_pdflatex_errors = False
        for line in stdout.splitlines():
            if line.startswith(":::"):
                try:
                    depthratio.append(float(line[4:]))
                except ValueError as err:
                    raise LatexCompilationError(
                        "pdflatex returned invalid equation depth data."
                    ) from err
            if line.startswith("!"):
                found_pdflatex_errors = True
            if found_pdflatex_errors:
                err_msg += line + "\n"

        if found_pdflatex_errors:
            raise LatexCompilationError(_trim_tool_log(err_msg))

        return pdf_filename, depthratio

    def run_gs_png(
        self, pdf_path: Path, output_prefix: str = "eq_img_", dpi: int | float = 250
    ) -> list[Path]:
        """Rasterize each page of ``pdf_path`` into a PNG via Ghostscript."""
        exe = self._tool_cmd("gs", "gs")
        self._require_executable(exe, GhostscriptNotFoundError, f"{exe} (Ghostscript)")
        output_template = self.temp_dir / f"{output_prefix}%05d.png"

        self._run_checked(
            [
                exe,
                "-dBATCH",
                "-q",
                "-dNOPAUSE",
                "-sDEVICE=pngalpha",
                f"-r{dpi}",
                "-dTextAlphaBits=4",
                "-dGraphicsAlphaBits=4",
                f"-sOutputFile={output_template}",
                str(pdf_path),
            ],
            exe,
            self.temp_dir,
            missing_error_cls=GhostscriptNotFoundError,
        )

        return sorted(self.temp_dir.glob(f"{output_prefix}*.png"))

    def run_latex_dvi(self, latex_content: str) -> Path:
        """Compile ``latex_content`` into a DVI file using ``latex``."""
        exe = self._tool_cmd("latex", "latex")
        latex_filename = self.temp_dir / "eq_list.tex"
        dvi_filename = self.temp_dir / "eq_list.dvi"
        latex_filename.write_text(latex_content, encoding="utf-8")

        stdout = self._run_tex_engine(exe, latex_filename)

        err_msg = ""
        found_latex_errors = False
        for line in stdout.splitlines():
            if line.startswith("!"):
                found_latex_errors = True
            if found_latex_errors:
                err_msg += line + "\n"

        if found_latex_errors:
            raise LatexCompilationError(_trim_tool_log(err_msg))

        return dvi_filename

    def run_dvisvgm_svg(
        self, dvi_path: Path, output_prefix: str = "eq_list", scale: int | float = 1.2
    ) -> list[Path]:
        """Convert each page of ``dvi_path`` into an SVG file using ``dvisvgm``."""
        exe = self._tool_cmd("dvisvgm", "dvisvgm")
        self._require_executable(exe, DvisvgmNotFoundError)
        output_template = self.temp_dir / f"{output_prefix}-%p.svg"

        self._run_checked(
            [
                exe,
                "-n",
                "-v",
                "1",
                "-p",
                "1-",
                "-c",
                f"{scale},{scale}",
                f"-o{output_template}",
                str(dvi_path),
            ],
            exe,
            self.temp_dir,
            missing_error_cls=DvisvgmNotFoundError,
        )

        return sorted(self.temp_dir.glob(f"{output_prefix}-*.svg"))

    def cleanup(self) -> None:
        """Remove the temporary working directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def __enter__(self) -> "LatexRunner":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()
