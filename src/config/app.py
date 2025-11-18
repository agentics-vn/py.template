"""Application-wide configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# Application Configuration
# =============================================================================

BASE_WEB_URL = os.getenv("BASE_WEB_URL", "http://localhost:4321")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# =============================================================================
# CORS Configuration
# =============================================================================

# Comma-separated list of allowed origins for CORS
# Examples:
#   Development: "http://localhost:4321,http://localhost:3000"
#   Production: "https://xemtarrot.vn"
ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", BASE_WEB_URL)
ALLOWED_ORIGINS = [origin.strip().rstrip("/") for origin in ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]
