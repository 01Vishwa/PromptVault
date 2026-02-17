# backend/tests/test_diff.py
"""Unit tests for the DiffService (no I/O needed)."""
from __future__ import annotations

from app.services.diff import DiffService


def test_identical_texts_produce_empty_diff() -> None:
    result = DiffService.compute(
        from_version=1, to_version=2,
        from_text="Hello world", to_text="Hello world",
    )
    assert result.unified_diff == ""
    assert result.from_version == 1
    assert result.to_version == 2


def test_different_texts_produce_diff() -> None:
    result = DiffService.compute(
        from_version=1, to_version=2,
        from_text="Hello {{name}}!",
        to_text="Hi {{name}}, welcome!",
    )
    assert len(result.unified_diff) > 0
    assert len(result.char_patches) > 0
    assert result.from_text == "Hello {{name}}!"
    assert result.to_text == "Hi {{name}}, welcome!"


def test_multiline_diff() -> None:
    from_text = "Line 1\nLine 2\nLine 3"
    to_text = "Line 1\nModified Line 2\nLine 3\nLine 4"
    result = DiffService.compute(
        from_version=1, to_version=2,
        from_text=from_text, to_text=to_text,
    )
    assert "Modified" in result.unified_diff
    assert "Line 4" in result.unified_diff


def test_version_hash_deterministic() -> None:
    """Verify the compute_hash function is deterministic."""
    from app.services.version import VersionService

    h1 = VersionService.compute_hash("Template", "System", {"temp": 0.7})
    h2 = VersionService.compute_hash("Template", "System", {"temp": 0.7})
    assert h1 == h2


def test_version_hash_sensitive_to_template() -> None:
    from app.services.version import VersionService

    h1 = VersionService.compute_hash("Template A", None, None)
    h2 = VersionService.compute_hash("Template B", None, None)
    assert h1 != h2


def test_version_hash_config_order_invariant() -> None:
    from app.services.version import VersionService

    h1 = VersionService.compute_hash("T", None, {"a": 1, "b": 2})
    h2 = VersionService.compute_hash("T", None, {"b": 2, "a": 1})
    assert h1 == h2
