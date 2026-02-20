import { Activity, Wifi, WifiOff, RefreshCw } from "lucide-react"
import { useAppStore } from "../../stores/appStore"
import { Badge } from "../ui/badge"
import { Button } from "../ui/button"
import { bootstrapApi, ingestionApi } from "../../lib/api"

export function Header() {
  const { 
    bootstrapRunning, 
    ingestionRunning, 
    wsConnected,
    settings,
    setBootstrapStats,
    setIngestionStats,
    setBootstrapRunning,
    setIngestionRunning,
  } = useAppStore()

  const handleRefresh = async () => {
    if (!settings.dbPath) return
    try {
      const [bootstrapStatus, ingestionStatus, bootstrapStats, ingestionStats] = await Promise.all([
        bootstrapApi.getStatus(),
        ingestionApi.getStatus(),
        bootstrapApi.getStats({ db_path: settings.dbPath }),
        ingestionApi.getStats({ db_path: settings.dbPath }),
      ])

      setBootstrapRunning(bootstrapStatus.data.running)
      setIngestionRunning(ingestionStatus.data.running)
      setBootstrapStats(bootstrapStats.data)
      setIngestionStats(ingestionStats.data)
    } catch (error) {
      console.error("Failed to refresh status:", error)
    }
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center space-x-4">
        <h1 className="text-lg font-semibold">DFS RAG Manager</h1>
        
        <div className="flex items-center space-x-2">
          <Badge variant={wsConnected ? "success" : "destructive"} className="gap-1">
            {wsConnected ? (
              <>
                <Wifi className="h-3 w-3" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                Disconnected
              </>
            )}
          </Badge>

          {bootstrapRunning && (
            <Badge variant="warning" className="gap-1">
              <RefreshCw className="h-3 w-3 animate-spin" />
              Bootstrap Running
            </Badge>
          )}

          {ingestionRunning && (
            <Badge variant="warning" className="gap-1">
              <RefreshCw className="h-3 w-3 animate-spin" />
              Ingestion Running
            </Badge>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <Activity className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>
    </header>
  )
}
