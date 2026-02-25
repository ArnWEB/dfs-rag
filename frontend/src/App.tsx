import { useEffect } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Layout } from "@/components/layout/Layout"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import DashboardPage from "@/pages/Dashboard"
import BootstrapPage from "@/pages/Bootstrap"
import IngestionPage from "@/pages/Ingestion"
import FilesPage from "@/pages/Files"
import SettingsPage from "@/pages/Settings"
import LoginPage from "@/pages/Login"
import { AuthProvider } from "@/lib/auth"
import { wsClient } from "@/lib/websocket"
import { useAppStore } from "@/stores/appStore"

function AppContent() {
  const {
    setWsConnected,
    setBootstrapRunning,
    setIngestionRunning,
    addActivityEvent,
  } = useAppStore()

  useEffect(() => {
    wsClient.connect()

    const unsubState = wsClient.onStateChange((state) => {
      setWsConnected(state === "connected")
    })

    const unsubscribers: (() => void)[] = []

    unsubscribers.push(
      wsClient.on("bootstrap:started", (data) => {
        const payload = data as { job_id: string; config: Record<string, unknown> }
        setBootstrapRunning(true)
        addActivityEvent({
          type: "bootstrap:started",
          message: `Bootstrap started: ${payload.config?.dfs_path}`,
        })
      })
    )

    unsubscribers.push(
      wsClient.on("bootstrap:completed", (data) => {
        const payload = data as { job_id: string; message: string }
        setBootstrapRunning(false)
        addActivityEvent({
          type: "bootstrap:completed",
          message: payload.message || "Bootstrap completed",
        })
      })
    )

    unsubscribers.push(
      wsClient.on("bootstrap:stopped", (data) => {
        const payload = data as { message: string }
        setBootstrapRunning(false)
        addActivityEvent({
          type: "bootstrap:stopped",
          message: payload.message || "Bootstrap stopped",
        })
      })
    )

    unsubscribers.push(
      wsClient.on("bootstrap:error", (data) => {
        const payload = data as { error: string }
        setBootstrapRunning(false)
        addActivityEvent({
          type: "bootstrap:error",
          message: `Bootstrap error: ${payload.error}`,
        })
      })
    )

    unsubscribers.push(
      wsClient.on("ingestion:started", (data) => {
        const payload = data as { job_id: string; config: Record<string, unknown> }
        setIngestionRunning(true)
        addActivityEvent({
          type: "ingestion:started",
          message: `Ingestion started: ${payload.config?.collection_name}`,
        })
      })
    )

    unsubscribers.push(
      wsClient.on("ingestion:completed", (data) => {
        const payload = data as { job_id: string; message: string }
        setIngestionRunning(false)
        addActivityEvent({
          type: "ingestion:completed",
          message: payload.message || "Ingestion completed",
        })
      })
    )

    unsubscribers.push(
      wsClient.on("ingestion:stopped", (data) => {
        const payload = data as { message: string }
        setIngestionRunning(false)
        addActivityEvent({
          type: "ingestion:stopped",
          message: payload.message || "Ingestion stopped",
        })
      })
    )

    unsubscribers.push(
      wsClient.on("ingestion:error", (data) => {
        const payload = data as { error: string }
        setIngestionRunning(false)
        addActivityEvent({
          type: "ingestion:error",
          message: `Ingestion error: ${payload.error}`,
        })
      })
    )

    return () => {
      unsubState()
      unsubscribers.forEach((unsub) => unsub())
      wsClient.disconnect()
    }
  }, [
    setWsConnected,
    setBootstrapRunning,
    setIngestionRunning,
    addActivityEvent,
  ])

  return (
    <Layout>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/bootstrap" element={<BootstrapPage />} />
        <Route path="/ingestion" element={<IngestionPage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppContent />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
