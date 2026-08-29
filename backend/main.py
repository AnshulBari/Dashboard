"""
Cricket Intelligence Platform — FastAPI Backend
================================================

REST API serving precomputed analytical data from PostgreSQL.

Design principles:
- All heavy computation happens in the Spark pipeline (offline)
- This API simply queries precomputed results
- Lightweight, fast responses
- Proper error handling and validation
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import logging

from backend.routes import players, teams, venues, matches, matchups, rankings, news, live, competitions, analytics
from backend.utils.database import init_db, close_db, engine

logger = logging.getLogger(__name__)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — startup and shutdown."""
    # Startup
    init_db()
    yield
    # Shutdown
    close_db()


app = FastAPI(
    title="Cricket Intelligence Platform",
    description="REST API for cricket analytics and intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:3000,http://localhost:8080"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(players.router, prefix="/api/players", tags=["Players"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(venues.router, prefix="/api/venues", tags=["Venues"])
app.include_router(matches.router, prefix="/api/matches", tags=["Matches"])
app.include_router(matchups.router, prefix="/api/matchups", tags=["Matchups"])
app.include_router(rankings.router, prefix="/api/rankings", tags=["Rankings"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(live.router, prefix="/api/live", tags=["Live"])
app.include_router(competitions.router, prefix="/api/competitions", tags=["Competitions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to prevent internal errors from leaking details."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {
        "name": "Cricket Intelligence Platform",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """Health check with lightweight database connectivity test."""
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )
