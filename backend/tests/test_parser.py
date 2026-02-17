# backend/tests/test_parser.py
"""Unit tests for template parser (no I/O, no mocks needed)."""
from __future__ import annotations

from app.services.parser import extract_variables, render_template


def test_extract_simple_variables() -> None:
    tpl = "Hello {{name}}, your order {{order_id}} is ready."
    assert extract_variables(tpl) == ["name", "order_id"]


def test_extract_with_spaces() -> None:
    tpl = "Hello {{ name }}, meet {{ friend }}."
    assert extract_variables(tpl) == ["friend", "name"]


def test_extract_no_variables() -> None:
    assert extract_variables("Hello world") == []


def test_extract_deduplicates() -> None:
    tpl = "{{x}} and {{x}} and {{y}}"
    assert extract_variables(tpl) == ["x", "y"]


def test_render_simple() -> None:
    result = render_template("Hello {{name}}!", {"name": "World"})
    assert result == "Hello World!"


def test_render_missing_variable_left_as_is() -> None:
    result = render_template("Hello {{name}}!", {})
    assert result == "Hello {{name}}!"


def test_render_multiple_variables() -> None:
    tpl = "Dear {{title}} {{name}}, welcome to {{company}}."
    result = render_template(tpl, {"title": "Dr", "name": "Smith", "company": "Acme"})
    assert result == "Dear Dr Smith, welcome to Acme."


def test_render_with_spaces_in_braces() -> None:
    result = render_template("Hello {{ name }}!", {"name": "World"})
    assert result == "Hello World!"
