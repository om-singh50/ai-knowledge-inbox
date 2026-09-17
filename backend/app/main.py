from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import init_db
import logging
from app.api.routers import ingest, items, query

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up API, initializing database...")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down API...")

app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(items.router, tags=["Items"])
app.include_router(query.router, tags=["Query"])

@app.get("/health")
def health_check():
    return {"status": "ok", "app_name": settings.app_name}

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.app_name}"}
