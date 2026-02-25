import axios from "axios"
import { keycloak } from "./keycloak"

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
})

api.interceptors.request.use(
  async (config) => {
    if (keycloak.authenticated) {
      const token = keycloak.token
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      keycloak.logout({ redirectUri: window.location.origin })
    }
    return Promise.reject(error)
  }
)

export interface BootstrapStats {
  total: number
  directories: number
  files: number
  discovered: number
  errors: number
  acl_captured: number
}

export interface IngestionStats {
  total: number
  pending: number
  completed: number
  failed: number
  ingesting: number
}

export interface BootstrapStatus {
  running: boolean
  job_id: string | null
  process_id: number | null
  start_time: number | null
  config: Record<string, unknown> | null
}

export interface IngestionStatus {
  running: boolean
  job_id: string | null
  process_id: number | null
  start_time: number | null
  config: Record<string, unknown> | null
}

export interface FileRecord {
  id: number
  file_path: string
  file_name: string
  parent_dir: string
  size: number | null
  mtime: number | null
  status: string
  ingestion_status: string | null
  ingestion_error: string | null
  ingested_at: string | null
  error: string | null
  is_directory: boolean
  first_seen: string
  last_seen: string
}

export interface FilesResponse {
  files: FileRecord[]
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }
}

export interface HealthStatus {
  status: string
  bootstrap_running: boolean
  ingestion_running: boolean
  ws_connections: number
}

export const bootstrapApi = {
  start: (config: {
    dfs_path: string
    db_path?: string
    workers?: number
    batch_size?: number
    timeout?: number
    log_level?: string
    acl_extractor?: string
  }) => api.post("/api/bootstrap/start", config),

  stop: () => api.post("/api/bootstrap/stop"),

  getStatus: () => api.get<BootstrapStatus>("/api/bootstrap/status"),

  getStats: (config: { db_path: string }) => api.post<BootstrapStats>("/api/bootstrap/stats", config),
}

export const ingestionApi = {
  start: (config: {
    db_path?: string
    collection_name?: string
    ingestor_host?: string
    ingestor_port?: number
    batch_size?: number
    checkpoint_interval?: number
    create_collection?: boolean
    resume?: boolean
    log_level?: string
  }) => api.post("/api/ingestion/start", config),

  stop: () => api.post("/api/ingestion/stop"),

  getStatus: () => api.get<IngestionStatus>("/api/ingestion/status"),

  getStats: (config: { db_path: string }) => api.post<IngestionStats>("/api/ingestion/stats", config),
}

export const filesApi = {
  list: (params: {
    search?: string
    status?: string
    ingestion_status?: string
    limit?: number
    page?: number
    db_path?: string
  }) => api.get<FilesResponse>("/api/files", { params }),
}

export const healthApi = {
  check: () => api.get<HealthStatus>("/api/health"),
}
