import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Layout } from "@/components/layout/Layout"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import DashboardPage from "@/pages/Dashboard"
import BootstrapPage from "@/pages/Bootstrap"
import IngestionPage from "@/pages/Ingestion"
import FilesPage from "@/pages/Files"
import SettingsPage from "@/pages/Settings"
import LoginPage from "@/pages/Login"
import SessionsPage from "./pages/Sessions"
import SessionDashboardPage from "./pages/SessionDashboard"
import { AuthProvider } from "@/lib/auth"

function AppContent() {
  return (
    <Layout>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/sessions/:id" element={<SessionDashboardPage />} />
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
