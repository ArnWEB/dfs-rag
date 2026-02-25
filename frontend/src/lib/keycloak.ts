import Keycloak from "keycloak-js"

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080",
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "dfs-rag",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "dfs-rag-frontend",
}

export const keycloak = new Keycloak(keycloakConfig)

export const keycloakConfigParams = {
  onLoad: "check-sso" as const,
  silentCheckSsoRedirectUri:
    window.location.origin + "/silent-check-sso.html",
  pkceMethod: "S256",
}

export default keycloak
