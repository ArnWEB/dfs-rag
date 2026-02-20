import { useState, useEffect, useCallback, useRef } from "react"
import { Search, ChevronLeft, ChevronRight, FileText, Folder, RefreshCw } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Button } from "../components/ui/button"
import { Label } from "../components/ui/label"
import { Badge } from "../components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select"
import { filesApi } from "../lib/api"

interface FileRecord {
  id: number
  file_path: string
  file_name: string
  parent_dir: string
  size: number | null
  mtime: number | null
  status: string
  ingestion_status: string | null
  is_directory: boolean
  last_seen: string
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "-"
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB", "TB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}

function StatusBadge({ status }: { status: string | null }) {
  const variants: Record<string, "default" | "success" | "warning" | "destructive" | "secondary"> = {
    pending: "secondary",
    discovered: "success",
    completed: "success",
    failed: "destructive",
    ingesting: "warning",
  }

  return (
    <Badge variant={variants[status || "pending"] || "secondary"}>
      {status || "pending"}
    </Badge>
  )
}

export default function FilesPage() {
  const [files, setFiles] = useState<FileRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [dbPath, setDbPath] = useState("")
  const [hasLoaded, setHasLoaded] = useState(false)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [ingestionStatusFilter, setIngestionStatusFilter] = useState<string>("all")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [total, setTotal] = useState(0)

  const dbPathRef = useRef(dbPath)
  dbPathRef.current = dbPath

  const fetchFiles = useCallback(async () => {
    const currentDbPath = dbPathRef.current
    if (!currentDbPath) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const params: Record<string, string | number> = {
        page,
        limit: 50,
        db_path: currentDbPath,
      }

      if (search.trim()) {
        params.search = search.trim()
      }
      if (statusFilter !== "all") {
        params.status = statusFilter
      }
      if (ingestionStatusFilter !== "all") {
        params.ingestion_status = ingestionStatusFilter
      }

      const response = await filesApi.list(params)
      setFiles(response.data.files)
      setTotalPages(response.data.pagination.pages)
      setTotal(response.data.pagination.total)
    } catch (error) {
      console.error("Failed to fetch files:", error)
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, ingestionStatusFilter])

  useEffect(() => {
    if (hasLoaded) {
      fetchFiles()
    }
  }, [hasLoaded, fetchFiles])

  useEffect(() => {
    setPage(1)
  }, [search, statusFilter, ingestionStatusFilter])

  const handleLoad = async () => {
    if (!dbPath) return
    setHasLoaded(true)
    setRefreshing(true)
    await fetchFiles()
    setRefreshing(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Files</h2>
          <p className="text-muted-foreground">
            Browse and search the manifest database
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleLoad} disabled={!dbPath || refreshing}>
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {!hasLoaded && (
        <div className="rounded-md bg-muted p-4">
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <Label htmlFor="files-db-path">Database Path</Label>
              <Input
                id="files-db-path"
                placeholder="./manifest.db"
                value={dbPath}
                onChange={(e) => setDbPath(e.target.value)}
                className="mt-1"
              />
            </div>
            <Button onClick={handleLoad} disabled={!dbPath || refreshing}>
              Load Files
            </Button>
          </div>
        </div>
      )}

      {hasLoaded && (
        <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>File Manifest</span>
            <Badge variant="outline">{total} files</Badge>
          </CardTitle>
          <CardDescription>
            View discovered files and their ingestion status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 items-center gap-2">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search files..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="discovered">Discovered</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>

              <Select value={ingestionStatusFilter} onValueChange={setIngestionStatusFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Ingestion" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Ingestion</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="ingesting">Ingesting</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Ingestion</TableHead>
                  <TableHead>Last Seen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="h-24 text-center">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : files.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="h-24 text-center">
                      No files found
                    </TableCell>
                  </TableRow>
                ) : (
                  files.map((file) => (
                    <TableRow key={file.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          {file.is_directory ? (
                            <Folder className="h-4 w-4 text-yellow-500" />
                          ) : (
                            <FileText className="h-4 w-4 text-blue-500" />
                          )}
                          {file.file_name}
                        </div>
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-muted-foreground">
                        {file.parent_dir}
                      </TableCell>
                      <TableCell>{formatBytes(file.size)}</TableCell>
                      <TableCell>
                        <StatusBadge status={file.status} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={file.ingestion_status} />
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {file.last_seen ? new Date(file.last_seen).toLocaleString() : "-"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Page {page} of {totalPages || 1}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
        )}
    </div>
  )
}
