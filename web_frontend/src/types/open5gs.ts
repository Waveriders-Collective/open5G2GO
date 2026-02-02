// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

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

export interface EnodebConfig {
  mme_ip: string;
  mme_port: number;
  plmn_id: string;
  tac: number;
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
  enodeb_config?: EnodebConfig;
  apns: {
    total: number;
    list: APN[];
  };
}

// Add Subscriber request with full 15-digit IMSI
export interface AddSubscriberRequest {
  imsi: string;           // Full 15-digit IMSI (e.g., "315010000000001")
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
  ambr?: {
    uplink: string;
    downlink: string;
  };
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

// eNodeB Status types
export interface ENodeBStatus {
  serial_number: string;
  config_name: string;
  location: string;
  ip_address?: string;
  port?: number;
  sctp_streams?: number;
  connected?: boolean;
  connected_at?: string;
}

// SNMP monitoring status for Baicells eNodeBs
export interface SNMPEnodebStatus {
  serial_number: string;
  config_name: string;
  location: string;
  reachable: boolean;
  error?: string;
  timestamp?: string;
  ip_address: string;
  identity: {
    serial_number?: string;
    product_type?: string;
    hardware_version?: string;
    software_version?: string;
    enodeb_name?: string;
    mac_address?: string;
  };
  cell: {
    status?: string;
    band_class?: number;
    bandwidth?: string;
    earfcn?: number;
    pci?: number;
    cell_id?: number;
    tac?: number;
  };
  connection: {
    s1_link_up: boolean;
    rf_enabled: boolean;
    ue_count: number;
  };
  performance: {
    ul_throughput_kbps?: number;
    dl_throughput_kbps?: number;
    ul_prb_pct?: number;
    dl_prb_pct?: number;
    cpu_utilization?: number;
  };
  kpis: {
    erab_success_pct?: number;
    rrc_success_pct?: number;
  };
  alarms: {
    count: number;
    sctp_failure: boolean;
    cell_unavailable: boolean;
  };
  tx_power: {
    current_dbm?: number;
    min_dbm?: number;
    max_dbm?: number;
  };
}

export interface EnodebStatusResponse {
  timestamp: string;
  s1ap: {
    available: boolean;
    connected_count: number;
    enodebs: ENodeBStatus[];
  };
  snmp?: {
    available: boolean;
    enabled: boolean;
    reachable_count: number;
    configured_count: number;
    enodebs: SNMPEnodebStatus[];
  };
  network?: {
    plmn: string;
    mcc: string;
    mnc: string;
    tac: number;
    network_name: string;
  };
}

// Service Monitoring types
export type ServiceStatus = 'running' | 'stopped' | 'error' | 'unknown';

export interface ServiceInfo {
  name: string;
  display_name: string;
  category: string;
  status: ServiceStatus;
  uptime: string | null;
  last_checked: string;
  details?: string;
}

export interface ServicesResponse {
  host: string;
  timestamp: string;
  check_method: 'docker' | 'process';
  services: ServiceInfo[];
  summary: {
    total: number;
    running: number;
    stopped: number;
    error: number;
    unknown: number;
  };
}
