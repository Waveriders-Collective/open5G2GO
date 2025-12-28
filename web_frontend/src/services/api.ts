/**
 * API Client for Surfcontrol Backend
 *
 * Provides typed methods for communicating with the FastAPI backend
 */

import axios, { AxiosInstance } from 'axios';
import type {
  ListSubscribersResponse,
  SystemStatusResponse,
  ActiveConnectionsResponse,
  NetworkConfigResponse,
  AddSubscriberRequest,
  AddSubscriberResponse,
  HealthCheckResponse,
  GetSubscriberResponse,
  UpdateSubscriberRequest,
  SubscriberOperationResponse,
} from '../types/attocore';
import type {
  DetectBTIResponse,
  SASStatusResponse,
  GnodebTimeResponse,
  SetTimeRequest,
  TimeSyncResponse,
  RestartCBRSResponse,
  AutomateSASRegistrationResponse,
} from '../types/gnodeb';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api/v1') {
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds for SSH operations
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await this.client.get<HealthCheckResponse>('/health');
    return response.data;
  }

  // List all subscribers
  async listSubscribers(host?: string): Promise<ListSubscribersResponse> {
    const response = await this.client.get<ListSubscribersResponse>('/subscribers', {
      params: { host },
    });
    return response.data;
  }

  // Get system status
  async getSystemStatus(host?: string): Promise<SystemStatusResponse> {
    const response = await this.client.get<SystemStatusResponse>('/status', {
      params: { host },
    });
    return response.data;
  }

  // Get active connections
  async getActiveConnections(host?: string): Promise<ActiveConnectionsResponse> {
    const response = await this.client.get<ActiveConnectionsResponse>('/connections', {
      params: { host },
    });
    return response.data;
  }

  // Get network configuration
  async getNetworkConfig(host?: string): Promise<NetworkConfigResponse> {
    const response = await this.client.get<NetworkConfigResponse>('/config', {
      params: { host },
    });
    return response.data;
  }

  // Add new subscriber
  async addSubscriber(data: AddSubscriberRequest): Promise<AddSubscriberResponse> {
    const response = await this.client.post<AddSubscriberResponse>('/subscribers', data);
    return response.data;
  }

  // Get single subscriber details
  async getSubscriber(imsi: string, host?: string): Promise<GetSubscriberResponse> {
    const response = await this.client.get<GetSubscriberResponse>(`/subscribers/${imsi}`, {
      params: { host },
    });
    return response.data;
  }

  // Update subscriber
  async updateSubscriber(imsi: string, data: UpdateSubscriberRequest): Promise<SubscriberOperationResponse> {
    const response = await this.client.put<SubscriberOperationResponse>(`/subscribers/${imsi}`, data);
    return response.data;
  }

  // Delete subscriber
  async deleteSubscriber(imsi: string, host?: string): Promise<SubscriberOperationResponse> {
    const response = await this.client.delete<SubscriberOperationResponse>(`/subscribers/${imsi}`, {
      params: { host },
    });
    return response.data;
  }

  // ============================================================================
  // gNodeB Management Methods
  // ============================================================================

  // Detect BTI radios
  async detectBTIRadios(attocoreHost?: string): Promise<DetectBTIResponse> {
    const response = await this.client.get<DetectBTIResponse>('/gnodeb/detect-bti', {
      params: { attocore_host: attocoreHost },
    });
    return response.data;
  }

  // Get SAS registration status
  async getSASStatus(gnodebIp: string): Promise<SASStatusResponse> {
    const response = await this.client.get<SASStatusResponse>('/gnodeb/sas-status', {
      params: { gnodeb_ip: gnodebIp },
    });
    return response.data;
  }

  // Get gNodeB system time
  async getGnodebTime(gnodebIp: string): Promise<GnodebTimeResponse> {
    const response = await this.client.get<GnodebTimeResponse>('/gnodeb/time', {
      params: { gnodeb_ip: gnodebIp },
    });
    return response.data;
  }

  // Sync gNodeB time to current UTC
  async syncGnodebTime(data: SetTimeRequest): Promise<TimeSyncResponse> {
    const response = await this.client.post<TimeSyncResponse>('/gnodeb/sync-time', data);
    return response.data;
  }

  // Restart CBRS process
  async restartCBRS(gnodebIp: string): Promise<RestartCBRSResponse> {
    const response = await this.client.post<RestartCBRSResponse>('/gnodeb/restart-cbrs', null, {
      params: { gnodeb_ip: gnodebIp },
    });
    return response.data;
  }

  // Automated SAS registration (time sync + CBRS restart)
  async automateSASRegistration(gnodebIp: string): Promise<AutomateSASRegistrationResponse> {
    const response = await this.client.post<AutomateSASRegistrationResponse>(
      '/gnodeb/automate-sas-registration',
      null,
      { params: { gnodeb_ip: gnodebIp } }
    );
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();
