from pathlib import Path

from quizml import cache


def test_clear_cache_removes_equation_and_conversion_entries(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    (cache_dir / "svg-pdf").mkdir(parents=True)
    (cache_dir / "equation.json").write_text("rendered")
    (cache_dir / "svg-pdf" / "image.pdf").write_bytes(b"converted")
    monkeypatch.setattr(cache, "CACHE_DIR", str(cache_dir))

    size = cache.clear_cache()

    assert size == len("rendered") + len(b"converted")
    assert not cache_dir.exists()


def test_equation_cache_hash_includes_tool_versions():
    first = cache.compute_hash("x^2", "PNG", {"pdflatex": "version 1"})
    second = cache.compute_hash("x^2", "PNG", {"pdflatex": "version 2"})

    assert first != second


def test_cache_size_counts_nested_files(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    nested = cache_dir / "svg-pdf"
    nested.mkdir(parents=True)
    (nested / "image.pdf").write_bytes(b"12345")
    monkeypatch.setattr(cache, "CACHE_DIR", str(cache_dir))

    assert cache.get_cache_size() == 5


def test_get_cache_dir_recreates_after_clear(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(cache, "CACHE_DIR", str(cache_dir))

    cache.get_cache_dir()
    cache.clear_cache()

    assert cache.get_cache_dir() == Path(cache_dir)
    assert cache_dir.is_dir()
