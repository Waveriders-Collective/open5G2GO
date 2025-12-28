"""
Grant History Storage

Stores SAS grant snapshots in MongoDB for historical display.
Since the Google SAS API doesn't provide grant history, we poll
periodically and store snapshots.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

# MongoDB collection name for grant history
GRANT_HISTORY_COLLECTION = "sas_grant_history"


class GrantHistoryStore:
    """
    Stores and retrieves SAS grant history from MongoDB.

    Grant snapshots are stored with timestamps and can be queried
    for a time range to display grant state changes over time.
    """

    def __init__(self, mongodb_uri: str = "mongodb://mongodb:27017/open5gs"):
        """
        Initialize the grant history store.

        Args:
            mongodb_uri: MongoDB connection URI.
        """
        self.mongodb_uri = mongodb_uri
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection] = None

    def _get_collection(self) -> Collection:
        """Get or create the MongoDB collection."""
        if self._collection is None:
            import os
            uri = os.getenv("MONGODB_URI", self.mongodb_uri)
            self._client = MongoClient(uri)
            db = self._client.get_default_database()
            self._collection = db[GRANT_HISTORY_COLLECTION]

            # Create indexes for efficient queries
            self._collection.create_index([
                ("serial_number", 1),
                ("timestamp", DESCENDING)
            ])
            self._collection.create_index("timestamp")

        return self._collection

    def store_snapshot(self, enodeb_status: Dict[str, Any]) -> bool:
        """
        Store a grant status snapshot for an eNodeB.

        Args:
            enodeb_status: Status dictionary from SAS client.

        Returns:
            True if stored successfully.
        """
        try:
            collection = self._get_collection()

            snapshot = {
                "timestamp": datetime.now(timezone.utc),
                "serial_number": enodeb_status.get("serial_number"),
                "fcc_id": enodeb_status.get("fcc_id"),
                "config_name": enodeb_status.get("config_name"),
                "sas_state": enodeb_status.get("sas_state"),
                "grants": enodeb_status.get("grants", []),
                "active_grant": enodeb_status.get("active_grant"),
            }

            collection.insert_one(snapshot)
            return True

        except Exception as e:
            logger.error(f"Failed to store grant snapshot: {e}")
            return False

    def store_all_snapshots(self, statuses: List[Dict[str, Any]]) -> int:
        """
        Store snapshots for all eNodeBs.

        Args:
            statuses: List of status dictionaries from SAS client.

        Returns:
            Number of snapshots stored.
        """
        stored = 0
        for status in statuses:
            if self.store_snapshot(status):
                stored += 1
        return stored

    def get_history(
        self,
        serial_number: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get grant history for an eNodeB.

        Args:
            serial_number: eNodeB serial number.
            hours: Number of hours of history to retrieve.

        Returns:
            List of historical snapshots, newest first.
        """
        try:
            collection = self._get_collection()
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            cursor = collection.find(
                {
                    "serial_number": serial_number,
                    "timestamp": {"$gte": cutoff}
                },
                {"_id": 0}
            ).sort("timestamp", DESCENDING)

            return list(cursor)

        except Exception as e:
            logger.error(f"Failed to get grant history: {e}")
            return []

    def get_grant_state_changes(
        self,
        serial_number: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get grant state changes (transitions) for an eNodeB.

        Args:
            serial_number: eNodeB serial number.
            hours: Number of hours of history.

        Returns:
            List of state change events.
        """
        history = self.get_history(serial_number, hours)

        if not history:
            return []

        changes = []
        prev_state = None
        prev_grant_state = None

        # Process in chronological order (reverse of query order)
        for snapshot in reversed(history):
            current_state = snapshot.get("sas_state")
            current_grant = snapshot.get("active_grant")
            current_grant_state = current_grant.get("state") if current_grant else None

            # Detect SAS state change
            if current_state != prev_state:
                changes.append({
                    "timestamp": snapshot["timestamp"],
                    "type": "sas_state",
                    "from_state": prev_state,
                    "to_state": current_state,
                })
                prev_state = current_state

            # Detect grant state change
            if current_grant_state != prev_grant_state:
                changes.append({
                    "timestamp": snapshot["timestamp"],
                    "type": "grant_state",
                    "from_state": prev_grant_state,
                    "to_state": current_grant_state,
                    "grant_id": current_grant.get("grant_id") if current_grant else None,
                })
                prev_grant_state = current_grant_state

        return changes

    def cleanup_old_history(self, hours: int = 24) -> int:
        """
        Remove history older than specified hours.

        Args:
            hours: Keep history newer than this many hours.

        Returns:
            Number of documents deleted.
        """
        try:
            collection = self._get_collection()
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            result = collection.delete_many({
                "timestamp": {"$lt": cutoff}
            })

            return result.deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")
            return 0


# =============================================================================
# Module-level Singleton
# =============================================================================

_history_store: Optional[GrantHistoryStore] = None


def get_history_store() -> GrantHistoryStore:
    """Get or create the singleton history store instance."""
    global _history_store
    if _history_store is None:
        _history_store = GrantHistoryStore()
    return _history_store
