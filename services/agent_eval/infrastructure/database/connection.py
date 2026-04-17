"""Async SQLAlchemy connection and session factory for the eval-core service.

Re-exports the shared ``DatabaseConnection`` from ``infrastructure.db.connection``
so all existing within-package imports continue to work unchanged.
"""
from infrastructure.db.connection import DatabaseConnection  # noqa: F401

__all__ = ["DatabaseConnection"]

