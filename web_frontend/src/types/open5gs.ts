/**
 * TypeScript types for Open5GS API responses
 *
 * These match the Pydantic models from the FastAPI backend
 * Updated for Open5GS 4G EPC (eNodeB, not gNodeB)
 */

// Common types
export interface Subscriber {
  imsi: string;
  name: string;
  apn: string;  // APN (4G terminology, was "service")
  ip: string;
}

export interface ENodeB {
  id: string;
  ip: string;
  name: string;
}

export interface Connection {
  imsi: string;
  name: string;
  cm_state: string;
  rm_state: string;
  ip?: string;
  apn?: string;  // APN instead of dnn for 4G
  session_id?: string;
}

export interface APN {
  name: string;
  downlink_kbps: string;
  uplink_kbps: string;
}

// API Response types
export interface ListSubscribersResponse {
  host: string;
  timestamp: string;
  total: number;
  subscribers: Subscriber[];
}

export interface SystemStatusResponse {
  host: string;
  system_name?: string;
  timestamp: string;
  subscribers: {
    provisioned: number;
    registered: number;
    connected: number;
  };
  enodebs: {
    total: number;
    list: ENodeB[];
  };
  health: {
    core_operational: boolean;
    has_active_connections: boolean;
    enodebs_connected: boolean;
    operational_status: 'fully_operational' | 'core_and_network_ready' | 'core_ready';
  };
}

export interface ActiveConnectionsResponse {
  host: string;
  timestamp: string;
  total_active: number;
  connections: Connection[];
}

export interface NetworkConfigResponse {
  host: string;
  timestamp: string;
  network_identity: {
    plmnid: string;
    mcc: string;
    mnc: string;
    network_name: string;
    tac: string;
  };
  apns: {
    total: number;
    list: APN[];
  };
}

// Simplified Add Subscriber for Open5GS with 4-digit IMSI entry
export interface AddSubscriberRequest {
  device_number: string;  // Last 4 digits of IMSI (e.g., "0001")
  name: string;           // Device name (e.g., "CAM-01")
  ip?: string;            // Optional static IP from 10.48.99.x pool
}

export interface AddSubscriberResponse {
  success: boolean;
  timestamp: string;
  subscriber: {
    imsi: string;
    name: string;
    ip: string;
    apn: string;
  };
  error?: string;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  service: string;
}

export interface ErrorResponse {
  error: string;
  details?: string;
  host?: string;
}

// Subscriber editing types
export interface UpdateSubscriberRequest {
  ip?: string;
  name?: string;
}

export interface GetSubscriberResponse {
  success: boolean;
  imsi: string;
  host: string;
  timestamp: string;
  data?: {
    security?: Record<string, unknown>;
    slice?: Record<string, unknown>[];
    ambr?: Record<string, unknown>;
  };
  error?: string;
}

export interface SubscriberOperationResponse {
  success: boolean;
  message?: string;
  imsi?: string;
  host?: string;
  timestamp?: string;
  changes?: string[];
  error?: string;
}

// eNodeB and SAS Status types
export interface GrantInfo {
  grant_id: string;
  state: string;
  frequency_mhz: number;
  max_eirp_dbm: number;
  channel_type: 'GAA' | 'PAL';
  expire_time: string;
}

export interface ENodeBStatus {
  serial_number: string;
  fcc_id: string;
  sas_state: string;
  config_name: string;
  location: string;
  active_grant?: GrantInfo;
  grants: GrantInfo[];
}

export interface EnodebStatusResponse {
  timestamp: string;
  s1ap: {
    available: boolean;
    connected_count: number;
    enodebs: ENodeBStatus[];
  };
  sas: {
    available: boolean;
    registered_count: number;
    authorized_count: number;
    enodebs: ENodeBStatus[];
  };
}

export interface GrantHistoryResponse {
  serial_number: string;
  timestamp: string;
  history: GrantInfo[];
}

export interface RefreshSasResponse {
  success: boolean;
  message: string;
  timestamp: string;
}
