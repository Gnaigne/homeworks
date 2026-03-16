import axios from "axios";

// API Base URL - proxy through Vite to avoid CORS
const API_BASE = "/api"; 

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// ============================================
// HEALTH CHECK
// ============================================

export const healthCheck = async () => {
  const response = await api.get("/health");
  return response.data;
};

// ============================================
// ASSETS API
// ============================================

export const assetsAPI = {
  // Create new asset
  create: async (data) => {
    const response = await api.post("/assets", data);
    return response.data;
  },

  // List assets with filters and pagination
  list: async (params = {}) => {
    const response = await api.get("/assets", { params });
    return response.data;
  },

  // Get single asset
  get: async (id) => {
    const response = await api.get(`/assets/${id}`);
    return response.data;
  },

  // Update asset
  update: async (id, data) => {
    const response = await api.put(`/assets/${id}`, data);
    return response.data;
  },

  // Delete asset
  delete: async (id) => {
    await api.delete(`/assets/${id}`);
  },
};

// ============================================
// SCANNING API
// ============================================

export const scanningAPI = {
  // Start a scan
  startScan: async (assetId, scanType) => {
    const response = await api.post(`/assets/${assetId}/scan`, {
      scan_type: scanType,
    });
    return response.data;
  },

  // List scan jobs for an asset
  listJobs: async (assetId, params = {}) => {
    const response = await api.get(`/assets/${assetId}/scans`, { params });
    return response.data;
  },

  // Get scan job status
  getJob: async (jobId) => {
    const response = await api.get(`/scan-jobs/${jobId}`);
    return response.data;
  },

  // Get scan results
  getResults: async (jobId) => {
    const response = await api.get(`/scan-jobs/${jobId}/results`);
    return response.data;
  },

  // Demo: Sync vs Async
  demo: async (assetId, scanTypes) => {
    const response = await api.post(`/assets/${assetId}/scan/demo`, {
      scan_types: scanTypes,
    });
    return response.data;
  },
};

// ============================================
// RESULTS API
// ============================================

export const resultsAPI = {
  // Get all results for an asset
  getAll: async (assetId) => {
    const response = await api.get(`/assets/${assetId}/results`);
    return response.data;
  },

  // Get subdomains
  getSubdomains: async (assetId, params = {}) => {
    const response = await api.get(`/assets/${assetId}/subdomains`, { params });
    return response.data;
  },

  // Get DNS records
  getDNS: async (assetId, params = {}) => {
    const response = await api.get(`/assets/${assetId}/dns`, { params });
    return response.data;
  },

  // Get WHOIS record
  getWHOIS: async (assetId) => {
    const response = await api.get(`/assets/${assetId}/whois`);
    return response.data;
  },

  // Get IP geolocation / ASN info
  getIP: async (assetId) => {
    const response = await api.get(`/assets/${assetId}/ip`);
    return response.data;
  },

  // Get SSL/TLS certificate info
  getSSL: async (assetId) => {
    const response = await api.get(`/assets/${assetId}/ssl`);
    return response.data;
  },

  // Get technology stack detection
  getTech: async (assetId) => {
    const response = await api.get(`/assets/${assetId}/tech`);
    return response.data;
  },

  // Get Certificate Transparency logs (crt.sh)
  getCertTrans: async (assetId, params = {}) => {
    const response = await api.get(`/assets/${assetId}/cert_trans`, { params });
    return response.data;
  },

  // Get port scan results
  getPort: async (assetId, params = {}) => {
    const response = await api.get(`/assets/${assetId}/port`, { params });
    return response.data;
  },
};

// ============================================
// ERROR HANDLING
// ============================================

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.error || error.message || "An error occurred";
    console.error("API Error:", message);
    return Promise.reject(new Error(message));
  },
);

export default api;
