from fastapi import APIRouter

from .routes import algorithms, auth, progress


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(algorithms.router)
api_router.include_router(progress.router)

