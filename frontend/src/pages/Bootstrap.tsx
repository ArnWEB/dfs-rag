import { useState, useEffect, useCallback, useRef } from "react"
import { Play, Square, FolderSearch, Loader2, RefreshCw } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAppStore } from "@/stores/appStore"
import { bootstrapApi } from "@/lib/api"

export default function BootstrapPage() {
  const {
    bootstrapStats,
    bootstrapRunning,
    setBootstrapStats,
    setBootstrapRunning,
    addActivityEvent,
  } = useAppStore()

  const [dfsPath, setDfsPath] = useState("")
  const [dbPath, setDbPath] = useState("")
  const [workers, setWorkers] = useState("8")
  const [batchSize, setBatchSize] = useState("500")
  const [timeout, setTimeout] = useState("5")
  const [aclExtractor, setAclExtractor] = useState("getfacl")
  const [logLevel, setLogLevel] = useState("INFO")
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dbPathRef = useRef(dbPath)
  dbPathRef.current = dbPath

  const fetchStatus = useCallback(async () => {
    try {
      const { data: status } = await bootstrapApi.getStatus()
      setBootstrapRunning(status.running)
      if (dbPathRef.current) {
        const { data: stats } = await bootstrapApi.getStats({ db_path: dbPathRef.current })
        setBootstrapStats(stats)
      }
    } catch (err) {
      console.error("Failed to fetch bootstrap status:", err)
    }
  }, [setBootstrapRunning, setBootstrapStats])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchStatus()
    setRefreshing(false)
  }

  const handleStart = async () => {
    if (!dfsPath.trim()) {
      setError("Please enter a DFS path")
      return
    }

    setLoading(true)
    setError(null)

    try {
      await bootstrapApi.start({
        dfs_path: dfsPath,
        db_path: dbPath,
        workers: parseInt(workers),
        batch_size: parseInt(batchSize),
        timeout: parseInt(timeout),
        acl_extractor: aclExtractor,
        log_level: logLevel,
      })

      setBootstrapRunning(true)
      addActivityEvent({
        type: "bootstrap:started",
        message: `Bootstrap started for: ${dfsPath}`,
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start bootstrap"
      setError(message)
      addActivityEvent({
        type: "bootstrap:error",
        message,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    setLoading(true)
    try {
      await bootstrapApi.stop()
      setBootstrapRunning(false)
      addActivityEvent({
        type: "bootstrap:stopped",
        message: "Bootstrap stopped by user",
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to stop bootstrap"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const progress = bootstrapStats?.total
    ? Math.round((bootstrapStats.discovered / bootstrapStats.total) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Bootstrap</h2>
        <p className="text-muted-foreground">
          Scan DFS share and build manifest database
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderSearch className="h-5 w-5" />
              Bootstrap Scan
            </CardTitle>
            <CardDescription>
              Scan file shares and extract metadata + ACLs
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="dfs-path">DFS Path</Label>
              <Input
                id="dfs-path"
                placeholder="e.g., /mnt/dfs_share or C:\\dfs_share"
                value={dfsPath}
                onChange={(e) => setDfsPath(e.target.value)}
                disabled={bootstrapRunning || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="db-path">Database Path</Label>
              <Input
                id="db-path"
                placeholder="./manifest.db"
                value={dbPath}
                onChange={(e) => setDbPath(e.target.value)}
                disabled={bootstrapRunning || loading}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="workers">Workers</Label>
                <Input
                  id="workers"
                  type="number"
                  min="1"
                  max="32"
                  value={workers}
                  onChange={(e) => setWorkers(e.target.value)}
                  disabled={bootstrapRunning || loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="batch-size">Batch Size</Label>
                <Input
                  id="batch-size"
                  type="number"
                  min="100"
                  max="5000"
                  value={batchSize}
                  onChange={(e) => setBatchSize(e.target.value)}
                  disabled={bootstrapRunning || loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timeout">Timeout (min)</Label>
                <Input
                  id="timeout"
                  type="number"
                  min="1"
                  max="30"
                  value={timeout}
                  onChange={(e) => setTimeout(e.target.value)}
                  disabled={bootstrapRunning || loading}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>ACL Extractor</Label>
                <Select
                  value={aclExtractor}
                  onValueChange={setAclExtractor}
                  disabled={bootstrapRunning || loading}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="getfacl">getfacl</SelectItem>
                    <SelectItem value="stat">stat</SelectItem>
                    <SelectItem value="noop">noop</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Log Level</Label>
                <Select
                  value={logLevel}
                  onValueChange={setLogLevel}
                  disabled={bootstrapRunning || loading}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DEBUG">DEBUG</SelectItem>
                    <SelectItem value="INFO">INFO</SelectItem>
                    <SelectItem value="WARNING">WARNING</SelectItem>
                    <SelectItem value="ERROR">ERROR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex gap-2 pt-4">
              {!bootstrapRunning ? (
                <Button onClick={handleStart} disabled={loading}>
                  {loading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  Start Scan
                </Button>
              ) : (
                <Button variant="destructive" onClick={handleStop} disabled={loading}>
                  {loading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Square className="mr-2 h-4 w-4" />
                  )}
                  Stop Scan
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Progress</span>
              <Badge variant={bootstrapRunning ? "warning" : "secondary"}>
                {bootstrapRunning ? "Running" : "Idle"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2 flex-1">
                <div className="flex justify-between text-sm">
                  <span>Scan Progress</span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={refreshing}
                className="ml-4"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{bootstrapStats?.total ?? 0}</div>
                <div className="text-sm text-muted-foreground">Total Scanned</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{bootstrapStats?.discovered ?? 0}</div>
                <div className="text-sm text-muted-foreground">Discovered</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{bootstrapStats?.files ?? 0}</div>
                <div className="text-sm text-muted-foreground">Files</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{bootstrapStats?.directories ?? 0}</div>
                <div className="text-sm text-muted-foreground">Directories</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{bootstrapStats?.acl_captured ?? 0}</div>
                <div className="text-sm text-muted-foreground">ACL Captured</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold text-destructive">
                  {bootstrapStats?.errors ?? 0}
                </div>
                <div className="text-sm text-muted-foreground">Errors</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
