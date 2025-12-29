"""
Service monitoring for Open5GS services.

Provides service status detection via Docker and process checking.
"""

import logging
import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Information about an Open5GS service."""
    name: str
    display_name: str
    category: str
    docker_name: Optional[str] = None
    process_name: Optional[str] = None


# Service definitions for 4G EPC mode
EPC_4G_SERVICES = [
    ServiceInfo("mme", "MME (Mobility Management Entity)", "4G EPC Core",
                docker_name="open5gs-mme", process_name="open5gs-mmed"),
    ServiceInfo("hss", "HSS (Home Subscriber Server)", "4G EPC Core",
                docker_name="open5gs-hss", process_name="open5gs-hssd"),
    ServiceInfo("pcrf", "PCRF (Policy & Charging Rules Function)", "4G EPC Core",
                docker_name="open5gs-pcrf", process_name="open5gs-pcrfd"),
    ServiceInfo("sgw-c", "SGW-C (Serving GW - Control)", "4G EPC Core",
                docker_name="open5gs-sgwc", process_name="open5gs-sgwcd"),
    ServiceInfo("sgw-u", "SGW-U (Serving GW - User Plane)", "4G EPC Core",
                docker_name="open5gs-sgwu", process_name="open5gs-sgwud"),
    ServiceInfo("pgw-c", "PGW-C (PDN GW - Control)", "4G EPC Core",
                docker_name="open5gs-smf", process_name="open5gs-smfd"),
    ServiceInfo("pgw-u", "PGW-U (PDN GW - User Plane)", "4G EPC Core",
                docker_name="open5gs-upf", process_name="open5gs-upfd"),
]

# Service definitions for 5G SA mode
SA_5G_SERVICES = [
    ServiceInfo("amf", "AMF (Access & Mobility Management Function)", "5G SA Core",
                docker_name="open5gs-amf", process_name="open5gs-amfd"),
    ServiceInfo("smf", "SMF (Session Management Function)", "5G SA Core",
                docker_name="open5gs-smf", process_name="open5gs-smfd"),
    ServiceInfo("upf", "UPF (User Plane Function)", "5G SA Core",
                docker_name="open5gs-upf", process_name="open5gs-upfd"),
    ServiceInfo("nrf", "NRF (Network Repository Function)", "5G SA Core",
                docker_name="open5gs-nrf", process_name="open5gs-nrfd"),
    ServiceInfo("udm", "UDM (Unified Data Management)", "5G SA Core",
                docker_name="open5gs-udm", process_name="open5gs-udmd"),
    ServiceInfo("udr", "UDR (Unified Data Repository)", "5G SA Core",
                docker_name="open5gs-udr", process_name="open5gs-udrd"),
    ServiceInfo("ausf", "AUSF (Authentication Server Function)", "5G SA Core",
                docker_name="open5gs-ausf", process_name="open5gs-ausfd"),
    ServiceInfo("pcf", "PCF (Policy Control Function)", "5G SA Core",
                docker_name="open5gs-pcf", process_name="open5gs-pcfd"),
    ServiceInfo("bsf", "BSF (Binding Support Function)", "5G SA Core",
                docker_name="open5gs-bsf", process_name="open5gs-bsfd"),
    ServiceInfo("nssf", "NSSF (Network Slice Selection Function)", "5G SA Core",
                docker_name="open5gs-nssf", process_name="open5gs-nssfd"),
]


class ServiceChecker:
    """Checks the status of Open5GS services."""

    def __init__(self):
        """Initialize service checker."""
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_docker_container(self, container_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if a Docker container is running.

        Args:
            container_name: Name of the Docker container

        Returns:
            Dictionary with status info or None if not found/available
        """
        if not self._docker_available:
            return None

        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{json .}}"],
                capture_output=True,
                timeout=10,
                text=True
            )

            if result.returncode != 0:
                return None

            # Parse each line as JSON
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    container = json.loads(line)
                    names = container.get("Names", "")
                    # Match container by suffix (e.g., "-mme", "-hss") to support
                    # different prefixes like open5gs-mme or open5g2go-mme
                    service_suffix = container_name.replace("open5gs", "")
                    if container_name in names or names.endswith(service_suffix):
                        state = container.get("State", "unknown")
                        running = state == "running"
                        return {
                            "running": running,
                            "status": state,
                            "container_id": container.get("ID", "")[:12],
                        }
                except json.JSONDecodeError:
                    continue

            return None
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"Error checking Docker container {container_name}: {e}")
            return None

    def _check_process(self, process_name: str) -> bool:
        """
        Check if a process is running.

        Args:
            process_name: Name of the process to check

        Returns:
            True if process is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_service_status(self, service: ServiceInfo) -> Dict[str, Any]:
        """
        Get status of a single service.

        Args:
            service: ServiceInfo object describing the service

        Returns:
            Dictionary with service status information
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Try Docker first
        if service.docker_name:
            docker_status = self._check_docker_container(service.docker_name)
            if docker_status is not None:
                return {
                    "name": service.name,
                    "display_name": service.display_name,
                    "category": service.category,
                    "status": "running" if docker_status["running"] else "stopped",
                    "uptime": None,
                    "last_checked": timestamp,
                    "details": f"Docker: {docker_status['container_id']}"
                }

        # Fall back to process checking
        if service.process_name:
            is_running = self._check_process(service.process_name)
            return {
                "name": service.name,
                "display_name": service.display_name,
                "category": service.category,
                "status": "running" if is_running else "stopped",
                "uptime": None,
                "last_checked": timestamp,
                "details": f"Process: {service.process_name}" if is_running else None
            }

        # Fallback to unknown
        return {
            "name": service.name,
            "display_name": service.display_name,
            "category": service.category,
            "status": "unknown",
            "uptime": None,
            "last_checked": timestamp,
            "details": "Unable to determine service status"
        }

    def get_all_services_status(self, mode: str = "4g_epc") -> Dict[str, Any]:
        """
        Get status of all services.

        Args:
            mode: Network mode - "4g_epc" or "5g_sa"

        Returns:
            Dictionary with all service statuses and summary
        """
        services = EPC_4G_SERVICES if mode == "4g_epc" else SA_5G_SERVICES

        statuses = []
        for service in services:
            status = self.get_service_status(service)
            statuses.append(status)

        # Calculate summary
        summary = {
            "total": len(statuses),
            "running": sum(1 for s in statuses if s["status"] == "running"),
            "stopped": sum(1 for s in statuses if s["status"] == "stopped"),
            "error": sum(1 for s in statuses if s["status"] == "error"),
            "unknown": sum(1 for s in statuses if s["status"] == "unknown"),
        }

        return {
            "host": "localhost",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check_method": "docker" if self._docker_available else "process",
            "services": statuses,
            "summary": summary
        }


# Global service checker instance
_service_checker: Optional[ServiceChecker] = None


def get_service_checker() -> ServiceChecker:
    """Get the global service checker instance."""
    global _service_checker
    if _service_checker is None:
        _service_checker = ServiceChecker()
    return _service_checker
