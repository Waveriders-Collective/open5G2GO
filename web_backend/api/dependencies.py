# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""
Dependencies for API routes.

Provides shared dependencies like service instances and configuration.
"""

from ..services.open5gs_service import get_open5gs_service, Open5GSService


def get_service() -> Open5GSService:
    """
    Dependency that provides the Open5GS service instance.

    Returns:
        Open5GSService: Singleton service instance
    """
    return get_open5gs_service()
