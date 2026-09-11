from fastapi import APIRouter

from app.api.v1 import admin, auth, civic, complaints

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(complaints.router)
api_router.include_router(civic.router)
api_router.include_router(admin.router)
