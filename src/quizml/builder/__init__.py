"""QuizML Build and Compilation Pipeline module.

Coordinates target dependency sorting (TopologicalSorter DAG), configuration resolution,
markdown transcoding, template rendering, and external build tool execution.
"""

from pathlib import Path

from quizml import quizmlyaml
from quizml.builder.config import load_config, resolve_targets
from quizml.builder.dag import (
    get_required_target_names_set,
    sort_targets_topologically,
)
from quizml.builder.scheduler import (
    TargetResult,
    compile_cmd_target,
    compile_render_target,
    execute_targets,
)
from quizml.filelocator import locate
from quizml.transcoder import MarkdownTranscoder


def compile_quiz(
    yaml_file: str | Path,
    targets: list[str] | str | None = None,
    build: bool = False,
    extra_context: dict | None = None,
    config: dict | None = None,
    config_path: str | Path | None = None,
) -> list[TargetResult]:
    """Compiles a QuizML YAML document to requested targets.

    :param yaml_file: Path to the quiz YAML file.
    :param targets: Optional specific target name or list of target names (e.g. 'pdf', ['latex', 'bb']).
    :param build: Whether to run post-compilation build commands (e.g. latexmk).
    :param extra_context: Extra variables to pass into template renderers.
    :param config: Pre-loaded config dictionary (optional).
    :param config_path: Path to custom quizml.cfg (optional).
    :return: List of TargetResult objects detailing success/failure of each target.
    """
    yaml_path = Path(yaml_file).resolve()
    cfg = config or load_config(
        config_file=str(config_path) if config_path else None,
        yaml_filename=str(yaml_path),
    )

    schema_file = cfg.get("schema_path", "schema.json")
    schema_path = locate.path(schema_file)
    doc, schema = quizmlyaml.load(yaml_path, validate=True, schema_path=schema_path)

    base_dir = yaml_path.parent
    transcoder = MarkdownTranscoder(doc, schema=schema, base_dir=str(base_dir))

    target_list = resolve_targets(
        cfg, doc, requested_targets=targets, yaml_filename=str(yaml_path)
    )
    is_targeted = bool(targets)

    return execute_targets(
        target_list,
        transcoder,
        build=build,
        is_targeted=is_targeted,
        extra_context=extra_context,
    )


__all__ = [
    "compile_quiz",
    "TargetResult",
    "load_config",
    "resolve_targets",
    "execute_targets",
    "compile_cmd_target",
    "compile_render_target",
    "get_required_target_names_set",
    "sort_targets_topologically",
]
