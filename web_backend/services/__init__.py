# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Waveriders Collective Inc.

"""Services package for Open5G2GO web backend."""

from .open5gs_service import Open5GSService, get_open5gs_service

__all__ = ["Open5GSService", "get_open5gs_service"]
