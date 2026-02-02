# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Configuration for the Open5G2GO Web Backend.

Loads settings from environment variables with sensible defaults.
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    app_name: str = "Open5G2GO Web API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # CORS Configuration
    allowed_origins: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost",       # Production frontend (same host)
        "http://localhost:8080",  # Docker exposed port
    ]

    # MongoDB Configuration
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_database: str = "open5gs"

    # System Configuration
    system_name: str = os.getenv("SYSTEM_NAME", "Open5G2GO")

    # Request Timeouts
    api_timeout: int = 30  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()
