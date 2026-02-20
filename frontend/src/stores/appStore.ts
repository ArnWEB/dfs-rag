import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { BootstrapStats, IngestionStats, ActivityEvent, AppSettings } from "../types"

interface AppState {
  bootstrapStats: BootstrapStats | null
  ingestionStats: IngestionStats | null
  bootstrapRunning: boolean
  ingestionRunning: boolean
  wsConnected: boolean
  activityLog: ActivityEvent[]
  settings: AppSettings

  setBootstrapStats: (stats: BootstrapStats | null) => void
  setIngestionStats: (stats: IngestionStats | null) => void
  setBootstrapRunning: (running: boolean) => void
  setIngestionRunning: (running: boolean) => void
  setWsConnected: (connected: boolean) => void
  addActivityEvent: (event: Omit<ActivityEvent, "id" | "timestamp">) => void
  clearActivityLog: () => void
  updateSettings: (settings: Partial<AppSettings>) => void
}

const generateId = () => Math.random().toString(36).substring(2, 9)

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      bootstrapStats: null,
      ingestionStats: null,
      bootstrapRunning: false,
      ingestionRunning: false,
      wsConnected: false,
      activityLog: [],
      settings: {
        dbPath: "",
        ingestorHost: "localhost",
        ingestorPort: 8082,
        logLevel: "INFO",
      },

      setBootstrapStats: (stats) => set({ bootstrapStats: stats }),
      setIngestionStats: (stats) => set({ ingestionStats: stats }),
      setBootstrapRunning: (running) => set({ bootstrapRunning: running }),
      setIngestionRunning: (running) => set({ ingestionRunning: running }),
      setWsConnected: (connected) => set({ wsConnected: connected }),
      
      addActivityEvent: (event) =>
        set((state) => ({
          activityLog: [
            {
              ...event,
              id: generateId(),
              timestamp: new Date().toISOString(),
            },
            ...state.activityLog.slice(0, 99),
          ],
        })),
      
      clearActivityLog: () => set({ activityLog: [] }),
      
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),
    }),
    {
      name: "dfs-rag-storage",
      partialize: (state) => ({ settings: state.settings }),
    }
  )
)
