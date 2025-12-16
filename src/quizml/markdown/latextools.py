import shutil
import subprocess
import tempfile
from pathlib import Path

from ..exceptions import (
    DvisvgmNotFoundError,
    GhostscriptNotFoundError,
    LatexCompilationError,
    LatexNotFoundError,
    Make4htNotFoundError,
)


class LatexRunner:
    def __init__(self, working_dir_prefix="quizml_latex_"):
        self._check_executables()
        self.temp_dir = Path(tempfile.mkdtemp(prefix=working_dir_prefix))

    def _check_executables(self):
        if not shutil.which("pdflatex"):
            raise LatexNotFoundError("pdflatex not found in PATH.")
        if not shutil.which("gs"):
            raise GhostscriptNotFoundError("gs (Ghostscript) not found in PATH.")
        if not shutil.which("latex"):
            raise LatexNotFoundError("latex not found in PATH.")
        if not shutil.which("dvisvgm"):
            raise DvisvgmNotFoundError("dvisvgm not found in PATH.")
        if not shutil.which("make4ht"):
            raise Make4htNotFoundError("make4ht not found in PATH.")

    def run_pdflatex(self, latex_content: str):
        latex_filename = self.temp_dir / "eq_list.tex"
        pdf_filename = self.temp_dir / "eq_list.pdf"

        latex_filename.write_text(latex_content)

        process = subprocess.Popen(
            ["pdflatex", "-interaction=nonstopmode", str(latex_filename)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.temp_dir,
        )

        stdout, _ = process.communicate()

        if process.returncode != 0:
            raise LatexCompilationError(f"pdflatex failed with return code {process.returncode}\n\n{stdout}")

        # Parse depth ratio from stdout
        depthratio = []
        err_msg = ''
        found_pdflatex_errors = False
        for line in stdout.splitlines():
            if line.startswith(':::'):
                depthratio.append(float(line[4:]))
            if line.startswith('!'):
                found_pdflatex_errors = True
            if found_pdflatex_errors:
                err_msg += line + '\n'

        if found_pdflatex_errors:
            raise LatexCompilationError(err_msg)

        return pdf_filename, depthratio

    def run_gs_png(self, pdf_path: Path, output_prefix="eq_img_"):
        output_template = self.temp_dir / f"{output_prefix}%05d.png"

        subprocess.check_call(
            [
                "gs",
                "-dBATCH",
                "-q",
                "-dNOPAUSE",
                "-sDEVICE=pngalpha",
                "-r250",
                "-dTextAlphaBits=4",
                "-dGraphicsAlphaBits=4",
                f"-sOutputFile={output_template}",
                str(pdf_path),
            ],
            cwd=self.temp_dir,
        )

        # Return a list of generated PNG files
        return sorted(self.temp_dir.glob(f"{output_prefix}*.png"))

    def run_latex_dvi(self, latex_content: str):
        latex_filename = self.temp_dir / "eq_list.tex"
        dvi_filename = self.temp_dir / "eq_list.dvi"

        latex_filename.write_text(latex_content)

        process = subprocess.Popen(
            ["latex", "-interaction=nonstopmode", str(latex_filename)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.temp_dir,
        )

        stdout, _ = process.communicate()

        if process.returncode != 0:
            raise LatexCompilationError(f"latex failed with return code {process.returncode}\n\n{stdout}")

        err_msg = ''
        found_latex_errors = False
        for line in stdout.splitlines():
            if line.startswith('!'):
                found_latex_errors = True
            if found_latex_errors:
                err_msg += line + '\n'

        if found_latex_errors:
            raise LatexCompilationError(err_msg)

        return dvi_filename

    def run_dvisvgm_svg(self, dvi_path: Path, output_prefix="eq_list"):
        output_template = self.temp_dir / f"{output_prefix}-%p.svg"

        subprocess.check_call(
            [
                "dvisvgm",
                "-n",
                '-v', '1',
                '-p', "1-",
                "-c", "1.2,1.2",
                f"-o{output_template}",
                str(dvi_path),
            ],
            cwd=self.temp_dir,
        )

        return sorted(self.temp_dir.glob(f"{output_prefix}-*.svg"))

    def run_make4ht_mathml(self, latex_content: str):
        latex_filename = self.temp_dir / "eq_list.tex"
        html_filename = self.temp_dir / "eq_list.html"

        latex_filename.write_text(latex_content)

        process = subprocess.Popen(
            ["make4ht", "-x", str(latex_filename), "xhtml,html5,mathml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.temp_dir,
        )

        stdout, _ = process.communicate()

        if process.returncode != 0:
            # make4ht returns errors on stdout
            raise LatexCompilationError(f"make4ht failed with return code {process.returncode}\n\n{stdout}")

        return html_filename


    def cleanup(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
