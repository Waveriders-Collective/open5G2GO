/**
 * API Client for openSurfControl Backend
 *
 * Provides typed methods for communicating with the FastAPI backend
 * Updated for Open5GS 4G EPC
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
} from '../types/open5gs';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api/v1') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
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
  async listSubscribers(): Promise<ListSubscribersResponse> {
    const response = await this.client.get<ListSubscribersResponse>('/subscribers');
    return response.data;
  }

  // Get system status
  async getSystemStatus(): Promise<SystemStatusResponse> {
    const response = await this.client.get<SystemStatusResponse>('/status');
    return response.data;
  }

  // Get active connections
  async getActiveConnections(): Promise<ActiveConnectionsResponse> {
    const response = await this.client.get<ActiveConnectionsResponse>('/connections');
    return response.data;
  }

  // Get network configuration
  async getNetworkConfig(): Promise<NetworkConfigResponse> {
    const response = await this.client.get<NetworkConfigResponse>('/config');
    return response.data;
  }

  // Add new subscriber (simplified for Open5GS)
  async addSubscriber(data: AddSubscriberRequest): Promise<AddSubscriberResponse> {
    const response = await this.client.post<AddSubscriberResponse>('/subscribers', data);
    return response.data;
  }

  // Get single subscriber details
  async getSubscriber(imsi: string): Promise<GetSubscriberResponse> {
    const response = await this.client.get<GetSubscriberResponse>(`/subscribers/${imsi}`);
    return response.data;
  }

  // Update subscriber
  async updateSubscriber(imsi: string, data: UpdateSubscriberRequest): Promise<SubscriberOperationResponse> {
    const response = await this.client.put<SubscriberOperationResponse>(`/subscribers/${imsi}`, data);
    return response.data;
  }

  // Delete subscriber
  async deleteSubscriber(imsi: string): Promise<SubscriberOperationResponse> {
    const response = await this.client.delete<SubscriberOperationResponse>(`/subscribers/${imsi}`);
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();
