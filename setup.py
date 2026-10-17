import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    """Copy repository documentation into the installable quizml package."""

    def run(self):
        super().run()
        source = Path(__file__).parent / "docs"
        target = Path(self.build_lib) / "quizml" / "docs"
        shutil.copytree(source, target, dirs_exist_ok=True)

    def get_outputs(self, include_bytecode=1):
        outputs = super().get_outputs(include_bytecode=include_bytecode)
        docs = Path(self.build_lib) / "quizml" / "docs"
        outputs.extend(str(path) for path in docs.rglob("*") if path.is_file())
        return outputs


setup(cmdclass={"build_py": BuildPy})
