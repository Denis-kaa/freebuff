from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    orders,
    offers,
    portfolio,
    community,
    notes,
    categories,
    files,
    health,
    messages,
    websocket
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(websocket.router, tags=["websocket"])

