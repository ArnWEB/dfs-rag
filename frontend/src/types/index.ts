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

export interface ActivityEvent {
  id: string
  type: string
  message: string
  timestamp: string
}

export interface AppSettings {
  dbPath: string
  ingestorHost: string
  ingestorPort: number
  logLevel: string
}
