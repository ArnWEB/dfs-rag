import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Play, Square, ArrowLeft, Upload, FolderSearch } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Progress } from "../components/ui/progress"
import { Badge } from "../components/ui/badge"
import { useAppStore } from "../stores/appStore"
import {
    sessionsApi,
    bootstrapApi,
    ingestionApi,
    filesApi
} from "../lib/api"
import type {
    SessionRecord,
    BootstrapStats,
    IngestionStats,
    FileRecord
} from "../lib/api"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"

export default function SessionDashboardPage() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()

    const {
        bootstrapRunning,
        ingestionRunning,
        setBootstrapRunning,
        setIngestionRunning,
        addActivityEvent
    } = useAppStore()

    const [session, setSession] = useState<SessionRecord | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const [bootstrapStats, setBootstrapStats] = useState<BootstrapStats | null>(null)
    const [ingestionStats, setIngestionStats] = useState<IngestionStats | null>(null)
    const [collectionName, setCollectionName] = useState("documents")

    // File Explorer states
    const [files, setFiles] = useState<FileRecord[]>([])
    const [totalFiles, setTotalFiles] = useState(0)
    const [page, setPage] = useState(1)
    const pageSize = 50

    const fetchFiles = useCallback(async (dbPath: string, currentPage: number) => {
        try {
            const resp = await filesApi.list({
                db_path: dbPath,
                limit: pageSize,
                page: currentPage
            })
            setFiles(resp.data.files || [])
            setTotalFiles(resp.data.pagination?.total || 0)
        } catch (e) {
            console.error("Failed to load files", e)
        }
    }, [])

    const fetchSession = useCallback(async () => {
        if (!id) return
        try {
            const resp = await sessionsApi.get(id)
            setSession(resp.data)

            // Attempt to load stats from the associated generated db_path
            try {
                const [bStats, iStats] = await Promise.all([
                    bootstrapApi.getStats({ db_path: resp.data.db_path }),
                    ingestionApi.getStats({ db_path: resp.data.db_path })
                ])
                setBootstrapStats(bStats.data)
                setIngestionStats(iStats.data)
                if (session?.db_path === resp.data.db_path) {
                    // Update only stats
                } else {
                    fetchFiles(resp.data.db_path, page)
                }
            } catch (e) {
                // Ignore DB not found on very first runs
            }
        } catch (err) {
            console.error("Failed to load session:", err)
            setError("Failed to load session details")
        } finally {
            setLoading(false)
        }
    }, [id, page, fetchFiles, session?.db_path])

    useEffect(() => {
        fetchSession()
    }, [id])

    const handleStartBootstrap = async () => {
        if (!session) return
        setError(null)
        setLoading(true)
        try {
            await bootstrapApi.start({
                dfs_path: session.dfs_path,
                db_path: session.db_path,
                session_id: session.id,
            })
            setBootstrapRunning(true)
            addActivityEvent({ type: "session:start_bootstrap", message: `Started bootstrap for ${session.name}` })
        } catch (err: any) {
            console.error(err)
            const errorMsg = err.response?.data?.detail || "Failed to start bootstrap"
            setError(errorMsg)
        } finally {
            setLoading(false)
        }
    }

    const handleStopBootstrap = async () => {
        try {
            await bootstrapApi.stop()
            setBootstrapRunning(false)
        } catch (err) {
            console.error(err)
        }
    }

    const handleStartIngestion = async () => {
        if (!session) return
        setError(null)
        setLoading(true)
        try {
            await ingestionApi.start({
                db_path: session.db_path,
                collection_name: collectionName,
                session_id: session.id,
            })
            setIngestionRunning(true)
            addActivityEvent({ type: "session:start_ingestion", message: `Started ingestion for ${session.name}` })
        } catch (err: any) {
            console.error(err)
            const detail = err.response?.data?.detail
            if (err.response?.status === 400 && detail?.active_ingestions) {
                const users = detail.active_ingestions.map((i: any) => i.user_name || i.user_id).join(', ')
                setError(`Max ingestions (5) reached. Currently running: ${users}`)
            } else {
                setError(typeof detail === 'string' ? detail : "Failed to start ingestion")
            }
        } finally {
            setLoading(false)
        }
    }

    const handleStopIngestion = async () => {
        if (!session) return
        try {
            await ingestionApi.stop({ session_id: session.id })
            setIngestionRunning(false)
            addActivityEvent({ type: "session:stop_ingestion", message: `Stopped ingestion for ${session.name}` })
        } catch (err: any) {
            console.error(err)
            setError(err.response?.data?.detail || "Failed to stop ingestion")
        }
    }

    if (loading && !session) return <div>Loading session...</div>
    if (!session) return <div>{error || "Session not found"}</div>

    const bootstrapProgress = bootstrapStats?.total ? Math.round(((bootstrapStats.discovered + bootstrapStats.errors) / bootstrapStats.total) * 100) : 0
    const ingestionProgress = ingestionStats?.total ? Math.round(((ingestionStats.completed + ingestionStats.failed) / ingestionStats.total) * 100) : 0

    return (
        <div className="space-y-6 max-w-6xl mx-auto p-4 md:p-8">
            <div className="flex items-center gap-4">
                <Button variant="outline" size="icon" onClick={() => navigate("/sessions")}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{session.name}</h2>
                    <div className="flex items-center gap-3 mt-1">
                        <Badge variant="outline" className="font-mono">{session.id}</Badge>
                        <Badge variant={
                            session.status === 'completed' ? 'success' :
                                session.status.includes('failed') ? 'destructive' :
                                    session.status === 'created' ? 'secondary' : 'warning'
                        }>
                            {session.status}
                        </Badge>
                    </div>
                </div>
            </div>

            <Card className="bg-muted/30 border-dashed">
                <CardContent className="pt-6">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground mr-2">Target Path:</span>
                            <span className="font-medium text-primary">{session.dfs_path}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground mr-2">Manifest Path:</span>
                            <span className="font-serif">{session.db_path}</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive border border-destructive/20 mt-4">
                    {error}
                </div>
            )}

            <Tabs defaultValue="overview" className="mt-6 w-full">
                <TabsList className="grid w-full grid-cols-2 max-w-[400px]">
                    <TabsTrigger value="overview">Pipeline Overview</TabsTrigger>
                    <TabsTrigger value="files">Folder View</TabsTrigger>
                </TabsList>

                <TabsContent value="overview">
                    <div className="grid gap-6 md:grid-cols-2 mt-4">

                        {/* BOOTSTRAP PIPELINE */}
                        <Card className="border-t-4 border-t-blue-500 shadow-md">
                            <CardHeader>
                                <CardTitle className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <FolderSearch className="h-5 w-5 text-blue-500" />
                                        Phase 1: Quick Bootstrap
                                    </div>
                                    <Badge variant={bootstrapRunning ? "warning" : "secondary"}>
                                        {bootstrapRunning ? "Running" : "Idle"}
                                    </Badge>
                                </CardTitle>
                                <CardDescription>Scan DFS and discover files</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>Discovery Progress</span>
                                        <span>{bootstrapProgress}%</span>
                                    </div>
                                    <Progress value={bootstrapProgress} className="h-2" />
                                </div>

                                <div className="grid grid-cols-2 gap-3 mb-4">
                                    <div className="rounded-md bg-muted/50 p-3">
                                        <div className="text-xl font-bold">{bootstrapStats?.total || 0}</div>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider">Total Scanned</div>
                                    </div>
                                    <div className="rounded-md bg-muted/50 p-3">
                                        <div className="text-xl font-bold text-blue-600">{bootstrapStats?.discovered || 0}</div>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider">Discovered</div>
                                    </div>
                                </div>

                                <div className="flex gap-2">
                                    {!bootstrapRunning ? (
                                        <Button onClick={handleStartBootstrap} disabled={loading || ingestionRunning} className="w-full">
                                            <Play className="mr-2 h-4 w-4" /> Start Quick Bootstrap
                                        </Button>
                                    ) : (
                                        <Button variant="destructive" onClick={handleStopBootstrap} disabled={loading} className="w-full">
                                            <Square className="mr-2 h-4 w-4" /> Stop Quick Bootstrap
                                        </Button>
                                    )}
                                </div>
                            </CardContent>
                        </Card>

                        {/* INGESTION PIPELINE */}
                        <Card className="border-t-4 border-t-purple-500 shadow-md">
                            <CardHeader>
                                <CardTitle className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Upload className="h-5 w-5 text-purple-500" />
                                        Phase 2: Ingest
                                    </div>
                                    <Badge variant={ingestionRunning ? "warning" : "secondary"}>
                                        {ingestionRunning ? "Running" : "Idle"}
                                    </Badge>
                                </CardTitle>
                                <CardDescription>Vectorize and store discovered files</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>Ingestion Progress</span>
                                        <span>{ingestionProgress}%</span>
                                    </div>
                                    <Progress value={ingestionProgress} className="h-2" />
                                </div>

                                <div className="grid grid-cols-2 gap-3 mb-4">
                                    <div className="rounded-md bg-muted/50 p-3">
                                        <div className="text-xl font-bold">{ingestionStats?.total || 0}</div>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider">To Ingest</div>
                                    </div>
                                <div className="rounded-md bg-muted/50 p-3">
                                        <div className="text-xl font-bold text-green-600">{ingestionStats?.completed || 0}</div>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider">Completed</div>
                                    </div>
                                </div>

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

                                <div className="flex gap-2">
                                    {!ingestionRunning ? (
                                        <Button onClick={handleStartIngestion} disabled={loading || bootstrapRunning || session.status === 'created' || session.status === 'bootstrapping'} className="w-full bg-purple-600 hover:bg-purple-700">
                                            <Play className="mr-2 h-4 w-4" /> Start Ingest
                                        </Button>
                                    ) : (
                                        <Button variant="destructive" onClick={handleStopIngestion} disabled={loading} className="w-full">
                                            <Square className="mr-2 h-4 w-4" /> Stop Ingest
                                        </Button>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="files">
                    <Card className="mt-4 shadow-md">
                        <CardHeader>
                            <CardTitle>Discovered Files</CardTitle>
                            <CardDescription>
                                Total records: {totalFiles}
                                <Button variant="outline" size="sm" className="ml-4" onClick={() => fetchFiles(session.db_path, page)}>Refresh Table</Button>
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="rounded-md border">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>File Name</TableHead>
                                            <TableHead>Type</TableHead>
                                            <TableHead>Boot Status</TableHead>
                                            <TableHead>Ingest Status</TableHead>
                                            <TableHead>Remark</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {files.map(f => (
                                            <TableRow key={f.id}>
                                                <TableCell className="font-medium max-w-[300px]" title={f.file_path}>
                                                    <div className="flex items-center gap-2">
                                                        {f.is_directory ? (
                                                            <FolderSearch className="h-4 w-4 text-blue-500 shrink-0" />
                                                        ) : (
                                                            <Upload className="h-4 w-4 text-muted-foreground shrink-0" />
                                                        )}
                                                        <span className="truncate">{f.file_name}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>{f.is_directory ? "Dir" : "File"}</TableCell>
                                                <TableCell>
                                                    <Badge variant={f.status === 'discovered' ? 'success' : 'secondary'}>{f.status}</Badge>
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant={
                                                        f.ingestion_status === 'completed' ? 'success' :
                                                            f.ingestion_status === 'failed' ? 'destructive' : 'secondary'
                                                    }>{f.ingestion_status || "N/A"}</Badge>
                                                </TableCell>
                                                <TableCell className="max-w-[200px] relative group">
                                                    <div className="truncate text-xs text-muted-foreground cursor-help">
                                                        {f.remarks || f.error || "-"}
                                                    </div>
                                                    {(f.remarks || f.error) && (
                                                        <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 bg-black text-white p-2 rounded text-xs w-64 shadow-lg pointer-events-none">
                                                            {f.remarks || f.error}
                                                            <div className="absolute top-full left-4 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-black"></div>
                                                        </div>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                        {files.length === 0 && (
                                            <TableRow>
                                                <TableCell colSpan={5} className="text-center py-6 text-muted-foreground">No files discovered yet.</TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </div>

                            <div className="flex items-center justify-between mt-4">
                                <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
                                <span className="text-sm text-muted-foreground">Page {page} of {Math.max(1, Math.ceil(totalFiles / pageSize))}</span>
                                <Button size="sm" variant="outline" disabled={page >= Math.ceil(totalFiles / pageSize)} onClick={() => setPage(page + 1)}>Next</Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
