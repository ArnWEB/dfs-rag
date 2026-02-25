import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react"
import { keycloak, keycloakConfigParams } from "./keycloak"

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: string | undefined
  login: () => void
  logout: () => void
  register: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

let keycloakInitialized = false

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState<string | undefined>(undefined)

  const updateAuthState = () => {
    setIsAuthenticated(keycloak.authenticated ?? false)
    if (keycloak.token) {
      const payload = JSON.parse(atob(keycloak.token.split(".")[1]))
      setUser(payload.preferred_username || payload.sub)
    }
  }

  useEffect(() => {
    if (keycloakInitialized) {
      updateAuthState()
      setIsLoading(false)
      return
    }

    keycloakInitialized = true

    const initKeycloak = async () => {
      try {
        const authenticated = await keycloak.init(keycloakConfigParams)
        setIsAuthenticated(authenticated)
        if (authenticated) {
          updateAuthState()
        }
      } catch (error) {
        console.error("Keycloak init error:", error)
      } finally {
        setIsLoading(false)
      }
    }

    initKeycloak()

    keycloak.onTokenExpired = () => {
      keycloak.updateToken(30).then(updateAuthState).catch(() => {
        keycloak.logout()
      })
    }

    keycloak.onAuthSuccess = updateAuthState
    keycloak.onAuthRefreshSuccess = updateAuthState

    const tokenExpired = setInterval(() => {
      keycloak.updateToken(30).catch(() => {
        keycloak.logout()
      })
    }, 60000)

    return () => clearInterval(tokenExpired)
  }, [])

  const login = () => {
    keycloak.login()
  }

  const logout = () => {
    keycloak.logout({ redirectUri: window.location.origin })
  }

  const register = () => {
    keycloak.register()
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        user,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
