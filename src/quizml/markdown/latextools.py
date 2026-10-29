import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..exceptions import (
    DvisvgmNotFoundError,
    GhostscriptNotFoundError,
    LatexCompilationError,
    LatexNotFoundError,
    LatexToolError,
)


def build_tex_env(search_dirs=None, base_env=None):
    """Build an environment dict with search_dirs prepended to TEXINPUTS."""
    env = dict(base_env if base_env is not None else os.environ)
    if not search_dirs:
        return env
    clean_dirs = []
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
        # Trailing os.pathsep ensures kpathsea still searches standard TEXMF trees
        env["TEXINPUTS"] = f"{prefix}{os.pathsep}"
    return env


def _trim_tool_log(*outputs):
    lines = [line for output in outputs if output for line in output.splitlines()]
    error_index = next(
        (i for i, line in enumerate(lines) if line.startswith("!")), None
    )
    if error_index is not None:
        lines = lines[error_index:]
    return "\n".join(lines[-40:])


def _process_failure(tool_name, returncode, stdout, stderr):
    details = _trim_tool_log(stdout, stderr) or "No diagnostic output was produced."
    return LatexCompilationError(
        f"{tool_name} failed with return code {returncode}\n{details}"
    )


def _launch_failure(tool_name, err, missing_error_cls=LatexNotFoundError):
    if isinstance(err, FileNotFoundError):
        return missing_error_cls(f"{tool_name} was not found while starting it.")
    detail = err.strerror or str(err)
    return LatexToolError(f"Could not start {tool_name}: {detail}")


def _communicate(process, tool_name):
    try:
        return process.communicate()
    except OSError as err:
        detail = err.strerror or str(err)
        raise LatexToolError(
            f"Could not collect output from {tool_name}: {detail}"
        ) from err


class LatexRunner:
    def __init__(
        self, working_dir_prefix="quizml_latex_", tools=None, tex_search_dirs=None
    ):
        self.temp_dir = Path(tempfile.mkdtemp(prefix=working_dir_prefix))
        self.tools = dict(tools or {})
        self.tex_search_dirs = list(tex_search_dirs or [])

    def _tex_env(self):
        return build_tex_env(self.tex_search_dirs) if self.tex_search_dirs else None

    def _tool_cmd(self, key, default):
        return self.tools.get(key, default)

    @staticmethod
    def _require_executable(name, error_cls, desc=None):
        if not shutil.which(name):
            desc = desc or name
            raise error_cls(f"{desc} not found in PATH.")

    @staticmethod
    def _run_checked(
        command, tool_name, cwd, missing_error_cls=LatexNotFoundError, env=None
    ):
        run_kwargs = {"capture_output": True, "text": True, "cwd": cwd, "check": False}
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

    def run_pdflatex(self, latex_content: str):
        exe = self._tool_cmd("pdflatex", "pdflatex")
        self._require_executable(exe, LatexNotFoundError)
        latex_filename = self.temp_dir / "eq_list.tex"
        pdf_filename = self.temp_dir / "eq_list.pdf"

        latex_filename.write_text(latex_content, encoding="utf-8")

        popen_kwargs = {
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

        # Parse depth ratio from stdout
        depthratio = []
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

    def run_gs_png(self, pdf_path: Path, output_prefix="eq_img_", dpi=250):
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

        # Return a list of generated PNG files
        return sorted(self.temp_dir.glob(f"{output_prefix}*.png"))

    def run_latex_dvi(self, latex_content: str):
        exe = self._tool_cmd("latex", "latex")
        self._require_executable(exe, LatexNotFoundError)
        latex_filename = self.temp_dir / "eq_list.tex"
        dvi_filename = self.temp_dir / "eq_list.dvi"

        latex_filename.write_text(latex_content, encoding="utf-8")

        popen_kwargs = {
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

    def run_dvisvgm_svg(self, dvi_path: Path, output_prefix="eq_list", scale=1.2):
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

    def cleanup(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
