import { useEffect, useState, useCallback, useRef } from "react"
import { Link } from "react-router-dom"
import {
  FolderSearch,
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ArrowRight,
  RefreshCw,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { useAppStore } from "../stores/appStore"
import { bootstrapApi, ingestionApi } from "../lib/api"

function StatsCard({
  title,
  value,
  icon: Icon,
  description,
  variant = "default",
}: {
  title: string
  value: number | string
  icon: React.ElementType
  description?: string
  variant?: "default" | "success" | "warning" | "destructive"
}) {
  const variantClasses: Record<string, string> = {
    default: "border-l-primary",
    success: "border-l-green-500",
    warning: "border-l-yellow-500",
    destructive: "border-l-red-500",
  }

  return (
    <Card className={`border-l-4 ${variantClasses[variant]}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  )
}

function ActivityFeed() {
  const { activityLog } = useAppStore()

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Activity Log</CardTitle>
        <CardDescription>Real-time events</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {activityLog.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity yet</p>
          ) : (
            activityLog.map((event) => (
              <div key={event.id} className="flex items-start space-x-2 text-sm">
                <div className="mt-0.5">
                  {event.type.includes("completed") ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : event.type.includes("error") || event.type.includes("failed") ? (
                    <XCircle className="h-4 w-4 text-red-500" />
                  ) : event.type.includes("started") ? (
                    <Clock className="h-4 w-4 text-blue-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                  )}
                </div>
                <div className="flex-1">
                  <p>{event.message}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const {
    bootstrapStats,
    ingestionStats,
    bootstrapRunning,
    ingestionRunning,
    settings,
    setBootstrapStats,
    setIngestionStats,
    setBootstrapRunning,
    setIngestionRunning,
  } = useAppStore()

  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [dbPath, setDbPath] = useState("")
  const [hasLoaded, setHasLoaded] = useState(false)

  const settingsRef = useRef(settings)
  settingsRef.current = settings

  const fetchDbPath = hasLoaded ? dbPath : ""

  const fetchStats = useCallback(async () => {
    const currentDbPath = hasLoaded ? dbPath : ""
    if (!currentDbPath) {
      setLoading(false)
      return
    }
    try {
      const [bootstrapStatus, ingestionStatus, bootstrapStatsRes, ingestionStatsRes] = await Promise.all([
        bootstrapApi.getStatus(),
        ingestionApi.getStatus(),
        bootstrapApi.getStats({ db_path: currentDbPath }),
        ingestionApi.getStats({ db_path: currentDbPath }),
      ])

      setBootstrapRunning(bootstrapStatus.data.running)
      setIngestionRunning(ingestionStatus.data.running)
      setBootstrapStats(bootstrapStatsRes.data)
      setIngestionStats(ingestionStatsRes.data)
    } catch (error) {
      console.error("Failed to fetch stats:", error)
    } finally {
      setLoading(false)
    }
  }, [setBootstrapStats, setIngestionStats, setBootstrapRunning, setIngestionRunning, hasLoaded, dbPath])

  useEffect(() => {
    if (hasLoaded && dbPath) {
      fetchStats()
    }
  }, [hasLoaded, dbPath, fetchStats])

  const handleRefresh = async () => {
    if (!dbPath) {
      return
    }
    setHasLoaded(true)
    setRefreshing(true)
    await fetchStats()
    setRefreshing(false)
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p>Loading...</p>
      </div>
    )
  }

  return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
            <p className="text-muted-foreground">
              Overview of your DFS RAG system
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {!fetchDbPath && (
          <div className="rounded-md bg-muted p-4">
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <Label htmlFor="dashboard-db-path">Database Path</Label>
                <Input
                  id="dashboard-db-path"
                  placeholder="./manifest.db"
                  value={dbPath}
                  onChange={(e) => setDbPath(e.target.value)}
                  className="mt-1"
                />
              </div>
              <Button onClick={handleRefresh} disabled={!dbPath || refreshing}>
                Load Stats
              </Button>
            </div>
          </div>
        )}

        {!fetchDbPath ? null : (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Files"
          value={bootstrapStats?.files ?? 0}
          icon={FileText}
          description="Files discovered"
        />
        <StatsCard
          title="Discovered"
          value={bootstrapStats?.discovered ?? 0}
          icon={FolderSearch}
          description="Ready for ingestion"
          variant="success"
        />
        <StatsCard
          title="Ingested"
          value={ingestionStats?.completed ?? 0}
          icon={CheckCircle}
          description={`of ${ingestionStats?.total ?? 0} discovered`}
          variant="success"
        />
        <StatsCard
          title="Failed"
          value={ingestionStats?.failed ?? 0}
          icon={XCircle}
          description="Ingestion errors"
          variant="destructive"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Start operations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button asChild className="w-full" disabled={bootstrapRunning}>
              <Link to="/bootstrap">
                <FolderSearch className="mr-2 h-4 w-4" />
                Start Bootstrap Scan
              </Link>
            </Button>
            <Button asChild className="w-full" disabled={ingestionRunning}>
              <Link to="/ingestion">
                <Upload className="mr-2 h-4 w-4" />
                Start Ingestion
              </Link>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <Link to="/files">
                <FileText className="mr-2 h-4 w-4" />
                Browse Files
                <ArrowRight className="ml-auto h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <ActivityFeed />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Bootstrap Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant={bootstrapRunning ? "warning" : "secondary"}>
                  {bootstrapRunning ? "Running" : "Idle"}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Directories</span>
                <span>{bootstrapStats?.directories ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">ACL Captured</span>
                <span>{bootstrapStats?.acl_captured ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Errors</span>
                <span className={bootstrapStats?.errors ? "text-red-500" : ""}>
                  {bootstrapStats?.errors ?? 0}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ingestion Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant={ingestionRunning ? "warning" : "secondary"}>
                  {ingestionRunning ? "Running" : "Idle"}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Pending</span>
                <span>{ingestionStats?.pending ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">In Progress</span>
                <span>{ingestionStats?.ingesting ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Success Rate</span>
                <span>
                  {ingestionStats && ingestionStats.total > 0
                    ? (
                        (ingestionStats.completed /
                          (ingestionStats.completed + ingestionStats.failed)) *
                        100
                      ).toFixed(1)
                    : 0}
                  %
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
        </>
        )}
    </div>
  )
}
