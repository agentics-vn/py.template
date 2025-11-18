import signal
import sys
import tomllib
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from api.routes import *
from config.app import LOG_LEVEL, ALLOWED_ORIGINS
from utils.logger import get_logger, setup_logging

setup_logging(level=LOG_LEVEL)
logger = get_logger()
logger.info(f"Logging initialized with level: {LOG_LEVEL}")
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")


def get_app_version() -> str:
    """Read application version from pyproject.toml.

    Returns:
        str: Application version string (e.g., "1.0.0"), or "0.0.0" if not found.
    """
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
            return pyproject_data.get("project", {}).get("version", "0.0.0")
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        logger.warning(f"Could not read version from pyproject.toml: {e}")
        return "0.0.0"


APP_VERSION = get_app_version()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle.

    This context manager handles:
    - Startup: Initialize agent and task registries
    - Shutdown: Clean up resources
    """
    logger.info("Initializing application registries...")
    logger.info("Application startup complete")

    yield

    logger.info("Shutting down application...")


app = FastAPI(
    title="Tarot API",
    description="Backend API service for tarot.vn",
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with detailed logging."""
    logger.error(f"HTTP {exc.status_code} error: {exc.detail}")
    logger.error(f"Request path: {request.url.path}")
    logger.error(f"Request method: {request.method}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging."""
    logger.error(f"Validation error on {request.url.path}")
    logger.error(f"Validation errors: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with full traceback logging."""
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception in {request.method} {request.url.path}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(f"Full traceback:\n{tb_str}")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        },
    )


class HTTP2PRIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "PRI" and request.url.path == "*":
            return Response(status_code=400, content="Bad Request")
        return await call_next(request)


app.add_middleware(HTTP2PRIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ],
    expose_headers=["Content-Length", "Content-Range"],
    max_age=600,
)


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "message": app.description,
        "version": app.version,
    }


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        logger.info("Starting server on host=0.0.0.0, port=8080")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_config=None,  # Disable uvicorn's default logging config
            access_log=True,  # Keep access logging but use our format
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server stopped")
