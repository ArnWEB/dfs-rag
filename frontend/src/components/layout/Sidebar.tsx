import { Link, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  FolderSearch,
  Upload,
  Files,
  Settings,
  Database,
  LogOut,
} from "lucide-react"
import { Button } from "../ui/button"
import { useAuth } from "@/lib/auth"

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/bootstrap", label: "Bootstrap", icon: FolderSearch },
  { href: "/ingestion", label: "Ingestion", icon: Upload },
  { href: "/files", label: "Files", icon: Files },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const location = useLocation()
  const { logout, user } = useAuth()

  return (
    <div className="flex h-full w-64 flex-col border-r bg-bank-blue">
      <div className="flex h-14 items-center border-b border-white/10 px-4">
        <Database className="mr-2 h-5 w-5 text-white" />
        <span className="font-semibold text-white">EXIM RAG</span>
      </div>
      
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Button
              key={item.href}
              variant="ghost"
              className={`w-full justify-start ${
                isActive
                  ? "bg-white/20 text-white font-medium"
                  : "text-white/70 hover:text-white hover:bg-white/10"
              }`}
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
      
      <div className="border-t border-white/10 p-4">
        {user && (
          <p className="mb-2 text-xs text-white/60">
            Logged in as: <span className="text-white">{user}</span>
          </p>
        )}
        <Button
          variant="ghost"
          className="w-full justify-start text-white/70 hover:text-white hover:bg-white/10"
          onClick={logout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </div>
  )
}
