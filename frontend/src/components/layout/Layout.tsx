import { Sidebar } from "./Sidebar"
import { Header } from "./Header"

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto bg-bank-gray-light p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
