"""Speed benchmarking harness: Piping vs All-in-One vs In-Memory Python API.

Measures wall-clock execution time across multiple iterations to evaluate
overhead from process startup, IPC pipes, and JSON serialization.
"""

import statistics
import subprocess
import time
from pathlib import Path

import quizml


def run_cmd(cmd_str: str) -> float:
    start = time.perf_counter()
    subprocess.run(
        cmd_str,
        shell=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return time.perf_counter() - start


def run_in_memory(yaml_file: Path, template: str) -> float:
    start = time.perf_counter()
    doc, _ = quizml.load(yaml_file)
    doc_tx = quizml.transcode(doc, target="latex")
    _ = quizml.render(doc_tx, template)
    return time.perf_counter() - start


def benchmark(iterations: int = 5):
    fixtures_dir = Path(__file__).parent / "fixtures"
    yaml_file = fixtures_dir / "test-markdown.yaml"
    template_name = "tcd-exam.tex.j2"

    print(f"Benchmarking QuizML on: {yaml_file.name}")
    print(f"Iterations: {iterations} runs each (discarding warmup)\n")

    # Warmup
    _ = run_in_memory(yaml_file, template_name)
    _ = run_cmd(f"uv run quizml {yaml_file} --render {template_name}")

    # 1. In-Memory Python API
    in_mem_times = []
    for _ in range(iterations):
        in_mem_times.append(run_in_memory(yaml_file, template_name))

    # 2. All-in-One CLI
    all_in_one_cmd = f"uv run quizml {yaml_file} --render {template_name}"
    all_in_one_times = []
    for _ in range(iterations):
        all_in_one_times.append(run_cmd(all_in_one_cmd))

    # 3. 2-Stage Unix Pipe (transcode -> render)
    two_stage_cmd = (
        f"uv run quizml {yaml_file} --transcode latex | "
        f"uv run quizml - --render {template_name}"
    )
    two_stage_times = []
    for _ in range(iterations):
        two_stage_times.append(run_cmd(two_stage_cmd))

    # 4. 3-Stage Unix Pipe (ingest -> transcode -> render)
    three_stage_cmd = (
        f"uv run quizml {yaml_file} --ingest | "
        f"uv run quizml - --transcode latex | "
        f"uv run quizml - --render {template_name}"
    )
    three_stage_times = []
    for _ in range(iterations):
        three_stage_times.append(run_cmd(three_stage_cmd))

    # 5. Component breakdown: Python interpreter startup
    py_startup_times = []
    for _ in range(iterations):
        py_startup_times.append(run_cmd("uv run python -c 'pass'"))

    # 6. Component breakdown: QuizML import time
    import_times = []
    for _ in range(iterations):
        import_times.append(run_cmd("uv run python -c 'import quizml'"))

    def fmt_stats(vals):
        med = statistics.median(vals) * 1000
        stdev = statistics.stdev(vals) * 1000 if len(vals) > 1 else 0.0
        return f"{med:6.1f} ms (± {stdev:4.1f} ms)"

    print("=" * 60)
    print(f"{'Mode':<32} {'Median Latency':<25}")
    print("=" * 60)
    print(f"{'1. In-Memory Python API':<32} {fmt_stats(in_mem_times)}")
    print(f"{'2. All-in-One CLI (--render)':<32} {fmt_stats(all_in_one_times)}")
    print(f"{'3. 2-Stage Pipe (tx | render)':<32} {fmt_stats(two_stage_times)}")
    print(f"{'4. 3-Stage Pipe (ing | tx | rnd)':<32} {fmt_stats(three_stage_times)}")
    print("-" * 60)
    print(f"{'Baseline: uv run python -c pass':<32} {fmt_stats(py_startup_times)}")
    print(f"{'Baseline: import quizml':<32} {fmt_stats(import_times)}")
    print("=" * 60)

    # Relative comparison
    base = statistics.median(in_mem_times)
    aio = statistics.median(all_in_one_times)
    p2 = statistics.median(two_stage_times)
    p3 = statistics.median(three_stage_times)

    print("\nRelative Analysis:")
    print(f"  • In-Memory Core Pipeline : {base * 1000:.1f} ms (pure compute)")
    print(
        f"  • All-in-One CLI Overhead : +{(aio - base) * 1000:.1f} ms (CLI startup + Argparse)"
    )
    print(
        f"  • 2-Stage Pipe Overhead   : +{(p2 - aio) * 1000:.1f} ms over All-in-One (1 extra process + JSON IPC)"
    )
    print(
        f"  • 3-Stage Pipe Overhead   : +{(p3 - aio) * 1000:.1f} ms over All-in-One (2 extra processes + 2 JSON IPCs)"
    )


if __name__ == "__main__":
    benchmark(iterations=7)
