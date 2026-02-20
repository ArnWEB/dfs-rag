import { useState } from "react"
import { Save, Settings as SettingsIcon } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { useAppStore } from "../stores/appStore"

export default function SettingsPage() {
  const { settings, updateSettings } = useAppStore()

  const [dbPath, setDbPath] = useState(settings.dbPath)
  const [ingestorHost, setIngestorHost] = useState(settings.ingestorHost)
  const [ingestorPort, setIngestorPort] = useState(settings.ingestorPort.toString())
  const [logLevel, setLogLevel] = useState(settings.logLevel)
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    updateSettings({
      dbPath,
      ingestorHost,
      ingestorPort: parseInt(ingestorPort),
      logLevel,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">
          Configure application settings
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="h-5 w-5" />
              Database
            </CardTitle>
            <CardDescription>
              Configure database connection
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="settings-db-path">Manifest Database Path</Label>
              <Input
                id="settings-db-path"
                placeholder="./manifest.db"
                value={dbPath}
                onChange={(e) => setDbPath(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Path to the SQLite database created by bootstrap
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="h-5 w-5" />
              NVIDIA RAG Ingestor
            </CardTitle>
            <CardDescription>
              Configure RAG ingestor connection
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="settings-ingestor-host">Host</Label>
              <Input
                id="settings-ingestor-host"
                placeholder="localhost"
                value={ingestorHost}
                onChange={(e) => setIngestorHost(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settings-ingestor-port">Port</Label>
              <Input
                id="settings-ingestor-port"
                type="number"
                placeholder="8082"
                value={ingestorPort}
                onChange={(e) => setIngestorPort(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="h-5 w-5" />
              Logging
            </CardTitle>
            <CardDescription>
              Configure logging settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Log Level</Label>
              <Select value={logLevel} onValueChange={setLogLevel}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DEBUG">DEBUG</SelectItem>
                  <SelectItem value="INFO">INFO</SelectItem>
                  <SelectItem value="WARNING">WARNING</SelectItem>
                  <SelectItem value="ERROR">ERROR</SelectItem>
                  <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Default log level for bootstrap and ingestion processes
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave}>
          <Save className="mr-2 h-4 w-4" />
          Save Settings
        </Button>
        {saved && (
          <span className="text-sm text-green-500">Settings saved successfully!</span>
        )}
      </div>
    </div>
  )
}
