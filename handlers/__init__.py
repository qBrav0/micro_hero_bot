from .start import router as start_router
from .user import router as user_router
from .admin import router as admin_router
from .common import router as common_router
from .reminder import router as reminder_router
from .event import router as event_router

__all__ = ["start_router", "user_router", "admin_router", "common_router", "reminder_router", "event_router"]
