# backend/app/services/parser.py
"""
Template variable parser.
Detects {{variable}} patterns in prompt templates.
"""
from __future__ import annotations

import re
from typing import List


# Matches {{var}}, {{ var }}, {{var_name}}, {{ my-var }}
_VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*\}\}")


def extract_variables(template_text: str) -> List[str]:
    """
    Extract unique variable names from a prompt template.
    Returns a sorted, deduplicated list.

    >>> extract_variables("Hello {{name}}, your order {{order_id}} is ready.")
    ['name', 'order_id']
    """
    matches = _VARIABLE_RE.findall(template_text)
    return sorted(set(matches))


def render_template(template_text: str, variables: dict[str, str]) -> str:
    """
    Render a prompt template by substituting {{variable}} placeholders.
    Missing variables are left as-is (fail-safe).

    >>> render_template("Hello {{name}}", {"name": "World"})
    'Hello World'
    """
    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1).strip()
        return variables.get(var_name, match.group(0))

    return _VARIABLE_RE.sub(replacer, template_text)
