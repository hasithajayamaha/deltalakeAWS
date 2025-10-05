import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Discovery endpoints
  async discoverResources(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/discover', { params });
    return response.data;
  }

  async listS3Buckets(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/resources/s3', { params });
    return response.data;
  }

  async getS3BucketDetails(bucketName: string, region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get(`/resources/s3/${bucketName}`, { params });
    return response.data;
  }

  async listGlueDatabases(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/resources/glue/databases', { params });
    return response.data;
  }

  async listGlueTables(database: string, region?: string) {
    const params = { database, ...(region && { region }) };
    const response = await this.client.get('/resources/glue/tables', { params });
    return response.data;
  }

  async listAthenaWorkgroups(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/resources/athena/workgroups', { params });
    return response.data;
  }

  async listFirehoseStreams(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/resources/firehose/streams', { params });
    return response.data;
  }

  async listIAMRoles(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/resources/iam/roles', { params });
    return response.data;
  }

  async listVPCEndpoints(region?: string) {
    const params = region ? { region } : {};
    const response = await this.client.get('/resources/vpc/endpoints', { params });
    return response.data;
  }

  // Cost endpoints
  async estimateCost(params?: {
    config_path?: string;
    scenario?: string;
    storage_gb?: number;
    monthly_queries?: number;
  }) {
    const response = await this.client.get('/cost/estimate', { params });
    return response.data;
  }

  async getCostScenarios(config_path?: string) {
    const params = config_path ? { config_path } : {};
    const response = await this.client.get('/cost/scenarios', { params });
    return response.data;
  }

  async getCostBreakdown(params: {
    config_path?: string;
    storage_gb: number;
    monthly_queries: number;
  }) {
    const response = await this.client.get('/cost/breakdown', { params });
    return response.data;
  }

  // Deployment endpoints
  async getDeploymentHistory() {
    const response = await this.client.get('/deploy/history');
    return response.data;
  }

  async getDeploymentStatus() {
    const response = await this.client.get('/deploy/status');
    return response.data;
  }

  async triggerDeployment(config: any) {
    const response = await this.client.post('/deploy', config);
    return response.data;
  }

  // Monitoring endpoints
  async getS3Metrics(bucket: string) {
    const response = await this.client.get('/metrics/s3', { params: { bucket } });
    return response.data;
  }

  async getAthenaMetrics(workgroup: string) {
    const response = await this.client.get('/metrics/athena', { params: { workgroup } });
    return response.data;
  }

  async getS3AccessLogs(bucket: string, limit: number = 100) {
    const response = await this.client.get('/logs/s3-access', { params: { bucket, limit } });
    return response.data;
  }

  // Config endpoints
  async getConfig() {
    const response = await this.client.get('/config');
    return response.data;
  }

  async validateConfig(config: any) {
    const response = await this.client.post('/config/validate', config);
    return response.data;
  }

  async getConfigTemplates() {
    const response = await this.client.get('/config/templates');
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  async getVersion() {
    const response = await this.client.get('/version');
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
