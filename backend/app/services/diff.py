# backend/app/services/diff.py
"""
Diff service — line-level (difflib) + character-level (diff-match-patch).
"""
from __future__ import annotations

import difflib

from diff_match_patch import diff_match_patch

from app.schemas.version import VersionDiff


class DiffService:
    """Stateless diff service — no DB access needed."""

    _dmp = diff_match_patch()

    @classmethod
    def compute(
        cls,
        from_version: int,
        to_version: int,
        from_text: str,
        to_text: str,
    ) -> VersionDiff:
        """
        Compute both diff types between two version texts.
        - unified_diff:  human-readable line diff (difflib)
        - char_patches:  character-level patches (diff-match-patch) for UI highlighting
        """
        # Line-level unified diff
        from_lines = from_text.splitlines(keepends=True)
        to_lines = to_text.splitlines(keepends=True)
        unified = "".join(
            difflib.unified_diff(
                from_lines,
                to_lines,
                fromfile=f"v{from_version}",
                tofile=f"v{to_version}",
                lineterm="",
            )
        )

        # Character-level diff patches
        diffs = cls._dmp.diff_main(from_text, to_text)
        cls._dmp.diff_cleanupSemantic(diffs)
        patches = cls._dmp.patch_toText(cls._dmp.patch_make(from_text, diffs))

        return VersionDiff(
            from_version=from_version,
            to_version=to_version,
            unified_diff=unified,
            char_patches=patches,
            from_text=from_text,
            to_text=to_text,
        )
