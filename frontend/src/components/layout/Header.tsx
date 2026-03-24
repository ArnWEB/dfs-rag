import { Activity } from "lucide-react"
import { useAppStore } from "../../stores/appStore"
import { Button } from "../ui/button"
import { bootstrapApi, ingestionApi } from "../../lib/api"

export function Header() {
  const {
    settings,
    setBootstrapStats,
    setIngestionStats,
  } = useAppStore()

  const handleRefresh = async () => {
    try {
      // Fetch stats if we have a dbPath
      if (settings.dbPath) {
        const [bStats, iStats] = await Promise.all([
          bootstrapApi.getStats({ db_path: settings.dbPath }),
          ingestionApi.getStats({ db_path: settings.dbPath })
        ])
        setBootstrapStats(bStats.data)
        setIngestionStats(iStats.data)
      }
    } catch (error) {
      console.error("Failed to refresh status:", error)
    }
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-nav">
      <div className="flex items-center space-x-4">
        <h1 className="text-lg font-semibold text-bank-blue-dark">EXIM RAG Ingest Manager</h1>
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
