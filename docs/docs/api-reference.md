# API Reference

Open5G2GO provides a REST API for programmatic access to subscriber management and system monitoring.

## Overview

| Property | Value |
|----------|-------|
| Base URL | `http://YOUR_HOST:8080/api/v1` |
| Content-Type | `application/json` |
| Authentication | None (MVP) |

### Interactive Documentation

The API provides interactive documentation at runtime:

- **Swagger UI**: `http://YOUR_HOST:8080/api/v1/docs`
- **ReDoc**: `http://YOUR_HOST:8080/api/v1/redoc`
- **OpenAPI Schema**: `http://YOUR_HOST:8080/api/v1/openapi.json`

---

## Health & System Endpoints

### Health Check

Check if the API is operational.

```
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "service": "Open5G2GO Web API"
}
```

### System Status

Get overall system health and statistics.

```
GET /api/v1/status
```

**Response:**
```json
{
  "timestamp": "2024-01-15 10:30:00 UTC",
  "system_name": "Open5G2GO",
  "subscribers": {
    "provisioned": 10,
    "registered": 1,
    "connected": 1
  },
  "enodebs": {
    "total": 1,
    "list": []
  },
  "health": {
    "core_operational": true,
    "database_connected": true,
    "has_active_connections": true,
    "enodebs_connected": true,
    "operational_status": "fully_operational"
  }
}
```

### Service Status

Get status of all Open5GS core services.

```
GET /api/v1/services
```

**Response:**
```json
{
  "host": "localhost",
  "timestamp": "2024-01-15T10:30:00.000000",
  "check_method": "docker",
  "services": [
    {
      "name": "mme",
      "display_name": "MME (Mobility Management Entity)",
      "category": "4G EPC Core",
      "status": "running",
      "uptime": null,
      "last_checked": "2024-01-15T10:30:00.000000",
      "details": "Docker: a1b2c3d4e5f6"
    }
  ],
  "summary": {
    "total": 7,
    "running": 5,
    "stopped": 2,
    "error": 0,
    "unknown": 0
  }
}
```

---

## Subscriber Management

### List All Subscribers

Retrieve all provisioned subscribers.

```
GET /api/v1/subscribers
```

**Response:**
```json
{
  "timestamp": "2024-01-15 10:30:00 UTC",
  "total": 10,
  "host": "Open5G2GO",
  "subscribers": [
    {
      "imsi": "315010000000001",
      "name": "CAM-01",
      "apn": "internet",
      "ip": "10.48.99.2"
    }
  ]
}
```

### Get Subscriber Details

Retrieve detailed information for a specific subscriber.

```
GET /api/v1/subscribers/{imsi}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `imsi` | string | 15-digit IMSI (e.g., `315010000000001`) |

**Response (200 OK):**
```json
{
  "success": true,
  "imsi": "315010000000001",
  "ambr": {
    "uplink": "100 Mbps",
    "downlink": "100 Mbps"
  },
  "data": {
    "imsi": "315010000000001",
    "security": {
      "k": "...",
      "opc": "..."
    },
    "slice": [...]
  }
}
```

**Response (404 Not Found):**
```json
{
  "error": "Subscriber not found",
  "details": "No subscriber with IMSI 315010000000001"
}
```

### Add Subscriber

Provision a new subscriber (SIM card) on the network.

```
POST /api/v1/subscribers
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `imsi` | string | Yes | Full 15-digit IMSI from SIM card |
| `name` | string | No | Friendly device name (max 50 chars) |
| `apn` | string | No | Access Point Name (default: "internet") |
| `ip` | string | No | Static IP address (auto-assigned if omitted) |

**Example Request:**
```json
{
  "imsi": "315010000000001",
  "name": "Camera-01",
  "apn": "internet"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "timestamp": "2024-01-15 10:30:00 UTC",
  "subscriber": {
    "imsi": "315010000000001",
    "name": "Camera-01",
    "ip": "10.48.99.2",
    "apn": "internet"
  }
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Invalid IMSI format",
  "details": "IMSI must be exactly 15 digits"
}
```

### Update Subscriber

Update an existing subscriber's properties.

```
PUT /api/v1/subscribers/{imsi}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `imsi` | string | 15-digit IMSI of subscriber to update |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | New device name |
| `apn` | string | No | New Access Point Name |
| `ip` | string | No | New static IP address |

At least one field must be provided.

**Example Request:**
```json
{
  "name": "Camera-02",
  "apn": "iot"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "imsi": "315010000000001",
  "changes": ["name → Camera-02", "apn → iot"],
  "message": "Subscriber updated: name → Camera-02, apn → iot"
}
```

### Delete Subscriber

Remove a subscriber from the network.

```
DELETE /api/v1/subscribers/{imsi}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `imsi` | string | 15-digit IMSI of subscriber to delete |

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Subscriber 315010000000001 deleted successfully"
}
```

!!! warning
    Deleting a subscriber immediately disconnects the device from the network.

---

## Network Configuration

### Get Network Configuration

Retrieve current network settings (read-only).

```
GET /api/v1/config
```

**Response:**
```json
{
  "timestamp": "2024-01-15 10:30:00 UTC",
  "host": "10.48.0.110",
  "network_identity": {
    "plmnid": "315010",
    "mcc": "315",
    "mnc": "010",
    "network_name": "Open5G2GO",
    "tac": "1"
  },
  "enodeb_config": {
    "mme_ip": "10.48.0.110",
    "mme_port": 36412,
    "plmn_id": "315-010",
    "tac": 1
  },
  "apns": {
    "total": 1,
    "list": [
      {
        "name": "internet",
        "downlink_kbps": "100 Mbps",
        "uplink_kbps": "50 Mbps"
      }
    ]
  },
  "ip_pool": {
    "subnet": null,
    "gateway": null,
    "start": "10.48.99.2",
    "end": "10.48.99.254"
  }
}
```

---

## eNodeB Management

### Get eNodeB Status

Retrieve connected eNodeB status and metrics.

```
GET /api/v1/enodeb/status
```

**Response:**
```json
{
  "timestamp": "2024-01-15 10:30:00 UTC",
  "s1ap": {
    "available": true,
    "connected_count": 1,
    "enodebs": [
      {
        "serial_number": "120200046421CKY0606",
        "config_name": "Nova-430i-Test",
        "location": "Test Lab",
        "ip_address": "10.48.0.159",
        "port": 36412,
        "connected": true,
        "connected_at": "2024-01-15 10:30:00"
      }
    ]
  },
  "snmp": {
    "available": false,
    "enabled": false,
    "reachable_count": 0,
    "enodebs": []
  },
  "network": {
    "plmn": "315010",
    "mcc": "315",
    "mnc": "010",
    "tac": "1",
    "network_name": "Open5G2GO"
  }
}
```

### Refresh eNodeB Status

Force a refresh of eNodeB status data.

```
POST /api/v1/enodeb/refresh
```

**Response:**
```json
{
  "success": true,
  "message": "SAS status refreshed",
  "timestamp": "2024-01-15 10:30:00 UTC"
}
```

---

## Active Connections

### Get Active Connections

Retrieve currently connected devices.

```
GET /api/v1/connections
```

**Response:**
```json
{
  "timestamp": "2024-01-15 10:30:00 UTC",
  "total_active": 2,
  "connections": [
    {
      "imsi": "315010000000001",
      "name": "Camera-01",
      "ip": "10.48.99.2",
      "status": "CONNECTED",
      "apn": "internet"
    }
  ]
}
```

---

## Error Handling

All endpoints return consistent error responses:

**Error Response Format:**
```json
{
  "error": "Error message",
  "details": "Additional context (debug mode only)"
}
```

**HTTP Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created (new subscriber) |
| 400 | Bad Request (validation error) |
| 404 | Not Found (subscriber doesn't exist) |
| 500 | Internal Server Error |

---

## Code Examples

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8080/api/v1"

# List all subscribers
response = requests.get(f"{BASE_URL}/subscribers")
subscribers = response.json()

# Add a new subscriber
new_device = {
    "imsi": "315010000000001",
    "name": "Camera-01"
}
response = requests.post(f"{BASE_URL}/subscribers", json=new_device)
result = response.json()

# Delete a subscriber
response = requests.delete(f"{BASE_URL}/subscribers/315010000000001")
```

### cURL

```bash
# Health check
curl http://localhost:8080/api/v1/health

# List subscribers
curl http://localhost:8080/api/v1/subscribers

# Add subscriber
curl -X POST http://localhost:8080/api/v1/subscribers \
  -H "Content-Type: application/json" \
  -d '{"imsi": "315010000000001", "name": "Camera-01"}'

# Get subscriber details
curl http://localhost:8080/api/v1/subscribers/315010000000001

# Update subscriber
curl -X PUT http://localhost:8080/api/v1/subscribers/315010000000001 \
  -H "Content-Type: application/json" \
  -d '{"name": "Camera-02"}'

# Delete subscriber
curl -X DELETE http://localhost:8080/api/v1/subscribers/315010000000001

# Get system status
curl http://localhost:8080/api/v1/status

# Get network config
curl http://localhost:8080/api/v1/config
```

### JavaScript (fetch)

```javascript
const BASE_URL = 'http://localhost:8080/api/v1';

// List subscribers
const response = await fetch(`${BASE_URL}/subscribers`);
const data = await response.json();

// Add subscriber
const newDevice = {
  imsi: '315010000000001',
  name: 'Camera-01'
};

const addResponse = await fetch(`${BASE_URL}/subscribers`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(newDevice)
});
```

---

## Rate Limiting

The MVP does not implement rate limiting. For production deployments, consider adding rate limiting via a reverse proxy (nginx, traefik) or API gateway.

## Authentication

The MVP does not implement authentication. All endpoints are publicly accessible. For production:

- Add API key authentication
- Implement JWT tokens
- Use a reverse proxy with authentication

---

## Changelog

| Version | Changes |
|---------|---------|
| 0.1.0 | Initial MVP release |
