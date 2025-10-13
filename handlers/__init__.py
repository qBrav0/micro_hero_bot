from .start import router as start_router
from .user import router as user_router
from .admin import router as admin_router
from .common import router as common_router

__all__ = ["start_router", "user_router", "admin_router", "common_router"]
