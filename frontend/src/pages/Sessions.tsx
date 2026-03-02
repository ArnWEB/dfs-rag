import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Plus, FolderSearch, RefreshCw, ChevronRight } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
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
import { sessionsApi } from "../lib/api"
import type { SessionRecord } from "../lib/api"

export default function SessionsPage() {
    const navigate = useNavigate()
    const [sessions, setSessions] = useState<SessionRecord[]>([])
    const [loading, setLoading] = useState(false)

    // New session form
    const [newSessionName, setNewSessionName] = useState("")
    const [newSessionPath, setNewSessionPath] = useState("")
    const [creating, setCreating] = useState(false)
    const [createError, setCreateError] = useState<string | null>(null)

    const fetchSessions = useCallback(async () => {
        setLoading(true)
        try {
            const response = await sessionsApi.list()
            setSessions(response.data)
        } catch (err) {
            console.error("Failed to fetch sessions:", err)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchSessions()
    }, [fetchSessions])

    const handleCreateSession = async () => {
        if (!newSessionName || !newSessionPath) return

        setCreating(true)
        setCreateError(null)
        try {
            const resp = await sessionsApi.create(newSessionName, newSessionPath)
            setNewSessionName("")
            setNewSessionPath("")
            navigate(`/sessions/${resp.data.id}`)
        } catch (err: any) {
            console.error("Failed to create session:", err)
            setCreateError(err.response?.data?.detail || "Failed to create session")
        } finally {
            setCreating(false)
        }
    }

    return (
        <div className="space-y-6 flex flex-col items-center max-w-5xl mx-auto p-4 md:p-8">
            <div className="w-full flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Sessions</h2>
                    <p className="text-muted-foreground">
                        Manage your Quick Bootstrap and Ingest sessions
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchSessions} disabled={loading}>
                    <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    Refresh
                </Button>
            </div>

            <div className="w-full grid gap-6 md:grid-cols-3">
                {/* Create Session Card */}
                <Card className="md:col-span-1 h-fit shadow-md border-primary/20 bg-gradient-to-b from-card to-card/50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Plus className="h-5 w-5 text-primary" />
                            New Session
                        </CardTitle>
                        <CardDescription>
                            Start a new Quick Ingest pipeline session
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="session-name">Session Name</Label>
                            <Input
                                id="session-name"
                                placeholder="e.g. Q4 Financials"
                                value={newSessionName}
                                onChange={(e) => setNewSessionName(e.target.value)}
                                disabled={creating}
                                className="bg-background/50"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="dfs-path">Target DFS Path</Label>
                            <Input
                                id="dfs-path"
                                placeholder="/mnt/data/reports"
                                value={newSessionPath}
                                onChange={(e) => setNewSessionPath(e.target.value)}
                                disabled={creating}
                                className="bg-background/50"
                            />
                        </div>
                        {createError && (
                            <div className="text-sm text-destructive">{createError}</div>
                        )}
                        <Button
                            className="w-full mt-2"
                            onClick={handleCreateSession}
                            disabled={creating || !newSessionName || !newSessionPath}
                        >
                            {creating ? "Creating..." : "Create Session"}
                        </Button>
                    </CardContent>
                </Card>

                {/* Sessions List Card */}
                <Card className="md:col-span-2 shadow-sm border-border/50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <FolderSearch className="h-5 w-5 text-muted-foreground" />
                            Recent Sessions
                        </CardTitle>
                        <CardDescription>
                            View and resume existing sessions
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border overflow-hidden">
                            <Table>
                                <TableHeader className="bg-muted/50">
                                    <TableRow>
                                        <TableHead>Name</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Target Path</TableHead>
                                        <TableHead>Created</TableHead>
                                        <TableHead className="w-[80px]"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {loading && sessions.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                                Loading sessions...
                                            </TableCell>
                                        </TableRow>
                                    ) : sessions.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                                No sessions found
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        sessions.map((session) => (
                                            <TableRow
                                                key={session.id}
                                                className="cursor-pointer hover:bg-muted/20 transition-colors"
                                                onClick={() => navigate(`/sessions/${session.id}`)}
                                            >
                                                <TableCell className="font-medium text-primary">
                                                    {session.name}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant={
                                                        session.status === 'completed' ? 'success' :
                                                            session.status.includes('failed') ? 'destructive' :
                                                                session.status === 'created' ? 'secondary' : 'warning'
                                                    }>
                                                        {session.status}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="max-w-[150px] truncate text-muted-foreground" title={session.dfs_path}>
                                                    {session.dfs_path}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground text-sm">
                                                    {new Date(session.created_at).toLocaleDateString()}
                                                </TableCell>
                                                <TableCell>
                                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                                        <ChevronRight className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
