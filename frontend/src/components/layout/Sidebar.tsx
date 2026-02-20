import { Link, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  FolderSearch,
  Upload,
  Files,
  Settings,
  Database,
} from "lucide-react"
import { Button } from "../ui/button"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/bootstrap", label: "Bootstrap", icon: FolderSearch },
  { href: "/ingestion", label: "Ingestion", icon: Upload },
  { href: "/files", label: "Files", icon: Files },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-4">
        <Database className="mr-2 h-5 w-5" />
        <span className="font-semibold">DFS RAG</span>
      </div>
      
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Button
              key={item.href}
              variant={isActive ? "secondary" : "ghost"}
              className={`w-full justify-start ${!isActive && "text-muted-foreground"}`}
              asChild
            >
              <Link to={item.href}>
                <item.icon className="mr-2 h-4 w-4" />
                {item.label}
              </Link>
            </Button>
          )
        })}
      </nav>
      
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">
          DFS RAG Manager v1.0
        </p>
      </div>
    </div>
  )
}
