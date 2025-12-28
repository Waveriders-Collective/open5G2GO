/**
 * TypeScript types for Attocore API responses
 *
 * These match the Pydantic models from the FastAPI backend
 */

// Common types
export interface Subscriber {
  imsi: string;
  name: string;
  service: string;
  ip: string;
}

export interface GNodeB {
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
  dnn?: string;
  session_id?: string;
}

export interface DNN {
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
  gnodebs: {
    total: number;
    list: GNodeB[];
  };
  health: {
    core_operational: boolean;
    has_active_connections: boolean;
    gnodebs_connected: boolean;
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
  dnns: {
    total: number;
    list: DNN[];
  };
}

export interface AddSubscriberRequest {
  device_number: number;
  name_prefix: string;
  dnn: string;
  ip_mode: 'old' | 'new';
  host?: string;
  imsi: string; // Required IMSI (15 digits)
}

export interface AddSubscriberResponse {
  success: boolean;
  timestamp: string;
  subscriber: {
    imsi: string;
    name: string;
    ip: string;
    dnn: string;
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
  dnn?: string;
  name?: string;
  host?: string;
}

export interface GetSubscriberResponse {
  success: boolean;
  imsi: string;
  host: string;
  timestamp: string;
  data?: {
    operatorSpecificData?: Record<string, any>;
    provisionedDataByPlmn?: Record<string, any>;
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
