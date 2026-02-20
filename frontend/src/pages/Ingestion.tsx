import { useState, useEffect, useCallback, useRef } from "react"
import { Play, Square, Upload, Loader2, RefreshCw } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Progress } from "../components/ui/progress"
import { Badge } from "../components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { useAppStore } from "../stores/appStore"
import { ingestionApi } from "../lib/api"

export default function IngestionPage() {
  const {
    ingestionStats,
    ingestionRunning,
    settings,
    setIngestionStats,
    setIngestionRunning,
    addActivityEvent,
  } = useAppStore()

  const [collectionName, setCollectionName] = useState("documents")
  const [dbPath, setDbPath] = useState("")
  const [ingestorHost, setIngestorHost] = useState(settings.ingestorHost)
  const [ingestorPort, setIngestorPort] = useState(settings.ingestorPort.toString())
  const [batchSize, setBatchSize] = useState("100")
  const [checkpointInterval, setCheckpointInterval] = useState("10")
  const [createCollection, setCreateCollection] = useState(true)
  const [resume, setResume] = useState(false)
  const [logLevel, setLogLevel] = useState("INFO")
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dbPathRef = useRef(dbPath)
  dbPathRef.current = dbPath

  const fetchStatus = useCallback(async () => {
    try {
      const { data: status } = await ingestionApi.getStatus()
      setIngestionRunning(status.running)
      if (dbPathRef.current) {
        const { data: stats } = await ingestionApi.getStats({ db_path: dbPathRef.current })
        setIngestionStats(stats)
      }
    } catch (err) {
      console.error("Failed to fetch ingestion status:", err)
    }
  }, [setIngestionRunning, setIngestionStats])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchStatus()
    setRefreshing(false)
  }

  const handleStart = async () => {
    setLoading(true)
    setError(null)

    try {
      await ingestionApi.start({
        db_path: dbPath,
        collection_name: collectionName,
        ingestor_host: ingestorHost,
        ingestor_port: parseInt(ingestorPort),
        batch_size: parseInt(batchSize),
        checkpoint_interval: parseInt(checkpointInterval),
        create_collection: createCollection,
        resume: resume,
        log_level: logLevel,
      })

      setIngestionRunning(true)
      addActivityEvent({
        type: "ingestion:started",
        message: `Ingestion started: ${collectionName}`,
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start ingestion"
      setError(message)
      addActivityEvent({
        type: "ingestion:error",
        message,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    setLoading(true)
    try {
      await ingestionApi.stop()
      setIngestionRunning(false)
      addActivityEvent({
        type: "ingestion:stopped",
        message: "Ingestion stopped by user",
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to stop ingestion"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const processed = (ingestionStats?.completed ?? 0) + (ingestionStats?.failed ?? 0)
  const total = ingestionStats?.total ?? 0
  const progress = total > 0 ? Math.round((processed / total) * 100) : 0
  const successRate =
    processed > 0 ? Math.round(((ingestionStats?.completed ?? 0) / processed) * 100) : 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Ingestion</h2>
        <p className="text-muted-foreground">
          Upload documents to NVIDIA RAG
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Ingestion Configuration
            </CardTitle>
            <CardDescription>
              Configure and start document ingestion
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="collection-name">Collection Name</Label>
              <Input
                id="collection-name"
                placeholder="documents"
                value={collectionName}
                onChange={(e) => setCollectionName(e.target.value)}
                disabled={ingestionRunning || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="ingestion-db-path">Database Path</Label>
              <Input
                id="ingestion-db-path"
                placeholder="./manifest.db"
                value={dbPath}
                onChange={(e) => setDbPath(e.target.value)}
                disabled={ingestionRunning || loading}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ingestor-host">Ingestor Host</Label>
                <Input
                  id="ingestor-host"
                  placeholder="localhost"
                  value={ingestorHost}
                  onChange={(e) => setIngestorHost(e.target.value)}
                  disabled={ingestionRunning || loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ingestor-port">Ingestor Port</Label>
                <Input
                  id="ingestor-port"
                  type="number"
                  placeholder="8082"
                  value={ingestorPort}
                  onChange={(e) => setIngestorPort(e.target.value)}
                  disabled={ingestionRunning || loading}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ingestion-batch-size">Batch Size</Label>
                <Input
                  id="ingestion-batch-size"
                  type="number"
                  min="1"
                  max="1000"
                  value={batchSize}
                  onChange={(e) => setBatchSize(e.target.value)}
                  disabled={ingestionRunning || loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="checkpoint-interval">Checkpoint Interval</Label>
                <Input
                  id="checkpoint-interval"
                  type="number"
                  min="1"
                  value={checkpointInterval}
                  onChange={(e) => setCheckpointInterval(e.target.value)}
                  disabled={ingestionRunning || loading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Log Level</Label>
              <Select
                value={logLevel}
                onValueChange={setLogLevel}
                disabled={ingestionRunning || loading}
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

            <div className="flex items-center gap-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="create-collection"
                  checked={createCollection}
                  onChange={(e) => setCreateCollection(e.target.checked)}
                  disabled={ingestionRunning || loading}
                  className="h-4 w-4"
                />
                <Label htmlFor="create-collection" className="text-sm font-normal">
                  Create collection
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="resume"
                  checked={resume}
                  onChange={(e) => setResume(e.target.checked)}
                  disabled={ingestionRunning || loading}
                  className="h-4 w-4"
                />
                <Label htmlFor="resume" className="text-sm font-normal">
                  Resume from checkpoint
                </Label>
              </div>
            </div>

            <div className="flex gap-2 pt-4">
              {!ingestionRunning ? (
                <Button onClick={handleStart} disabled={loading}>
                  {loading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  Start Ingestion
                </Button>
              ) : (
                <Button variant="destructive" onClick={handleStop} disabled={loading}>
                  {loading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Square className="mr-2 h-4 w-4" />
                  )}
                  Stop Ingestion
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Progress</span>
              <Badge variant={ingestionRunning ? "warning" : "secondary"}>
                {ingestionRunning ? "Running" : "Idle"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2 flex-1">
                <div className="flex justify-between text-sm">
                  <span>Ingestion Progress</span>
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
                <div className="text-2xl font-bold">{total}</div>
                <div className="text-sm text-muted-foreground">Total Files</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{processed}</div>
                <div className="text-sm text-muted-foreground">Processed</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold text-green-500">
                  {ingestionStats?.completed ?? 0}
                </div>
                <div className="text-sm text-muted-foreground">Completed</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold text-destructive">
                  {ingestionStats?.failed ?? 0}
                </div>
                <div className="text-sm text-muted-foreground">Failed</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold text-yellow-500">
                  {ingestionStats?.pending ?? 0}
                </div>
                <div className="text-sm text-muted-foreground">Pending</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-2xl font-bold">{successRate}%</div>
                <div className="text-sm text-muted-foreground">Success Rate</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
