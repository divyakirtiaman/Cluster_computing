"""
CineMatch FastAPI Application Entrypoint
Configures CORS, custom performance monitoring middleware, global exception handlers,
and registers all API v1 service routers.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.database import connect_to_mongo, close_mongo_connection, is_mongo_connected
from backend.app.core.cache import cache_service
from backend.app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    await connect_to_mongo()
    await cache_service.connect()
    yield
    # Shutdown tasks
    await cache_service.close()
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade AI Movie Recommendation Engine powered by FastAPI & Apache Spark MLlib.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Custom Performance Monitoring Middleware (X-Process-Time)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if isinstance(settings.BACKEND_CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred.", "error": str(exc)}
    )

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health and readiness probe reporting MongoDB and Redis cache states."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "backends": {
            "mongodb": "connected" if is_mongo_connected() else "offline",
            "redis": "connected" if cache_service.is_connected else "in-memory-fallback"
        }
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API. Visit /docs for interactive Swagger UI."
    }
