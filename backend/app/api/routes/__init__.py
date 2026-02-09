"""Axiom AI API Routes.

Route handlers for chat and health endpoints.
"""

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router

__all__ = ["chat_router", "health_router"]
