from fastapi import APIRouter
from app.api.v1 import receipts, categories, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])

