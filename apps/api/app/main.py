from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.api.v1.routes import router as v1_router
from apps.api.app.config import settings
from apps.api.app.db import init_db

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered German tax filing assistant with ELSTER field mapping",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
init_db()
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.environment,
        "docs": "/docs",
    }
