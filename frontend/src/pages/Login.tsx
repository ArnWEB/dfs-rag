import { LogIn, Database } from "lucide-react"
import { Navigate } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { Button } from "@/components/ui/button"

export default function LoginPage() {
  const { login, isLoading, isAuthenticated } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bank-gray-light p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-bank-blue shadow-lg">
            <Database className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-bank-blue-dark">EXIM RAG</h1>
          <p className="text-bank-gray-text">Ingest Manager</p>
        </div>

        <div className="rounded-lg border border-bank-gray-border bg-white p-8 shadow-card">
          <div className="mb-6 text-center">
            <h2 className="text-lg font-semibold text-bank-blue-dark">Welcome Back</h2>
            <p className="text-sm text-bank-gray-text">Sign in to continue</p>
          </div>

          <Button
            onClick={login}
            disabled={isLoading}
            className="w-full h-11 bg-bank-blue hover:bg-bank-blue-dark text-white font-medium rounded-bank"
            size="lg"
          >
            <LogIn className="mr-2 h-4 w-4" />
            {isLoading ? "Signing in..." : "Sign in with Keycloak"}
          </Button>

          <p className="mt-6 text-center text-xs text-bank-gray-text">
            You will be redirected to Keycloak for authentication.
            <br />
            Use LDAP credentials (e.g., riemann / password)
          </p>
        </div>

        <p className="mt-8 text-center text-xs text-bank-gray-text/70">
          Protected by Keycloak • Enterprise Security
        </p>
      </div>
    </div>
  )
}
