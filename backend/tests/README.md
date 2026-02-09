# Axiom AI Test Suite

This directory contains all unit and integration tests for Axiom AI.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_config.py       # Configuration tests
├── test_tools.py        # Tool system tests
├── test_agents.py       # Agent tests
└── test_api.py          # API endpoint tests
```
