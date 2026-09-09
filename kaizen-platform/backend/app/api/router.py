from fastapi import APIRouter

from app.api.routes import auth, google_oauth, health, internal, notifications, productivity

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(google_oauth.router)
api_router.include_router(productivity.router)
api_router.include_router(notifications.router)
api_router.include_router(internal.router)
