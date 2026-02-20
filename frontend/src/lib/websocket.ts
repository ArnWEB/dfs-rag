type EventCallback = (data: unknown) => void

type ConnectionState = "connecting" | "connected" | "disconnected" | "error"

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  private maxReconnectDelay = 30000
  private listeners: Map<string, Set<EventCallback>> = new Map()
  private state: ConnectionState = "disconnected"
  private stateListeners: Set<(state: ConnectionState) => void> = new Set()
  private messageQueue: { type: string; data: unknown }[] = []
  private pingInterval: number | null = null

  constructor(url: string) {
    this.url = url
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.setState("connecting")

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log("WebSocket connected")
        this.setState("connected")
        this.reconnectAttempts = 0
        this.reconnectDelay = 1000
        this.startPing()
        this.flushQueue()
      }

      this.ws.onclose = (event) => {
        console.log("WebSocket closed", event.code, event.reason)
        this.setState("disconnected")
        this.stopPing()
        
        if (!event.wasClean) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error("WebSocket error", error)
        this.setState("error")
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error("Failed to parse WebSocket message", error)
        }
      }
    } catch (error) {
      console.error("Failed to create WebSocket", error)
      this.setState("error")
      this.scheduleReconnect()
    }
  }

  disconnect(): void {
    this.stopPing()
    if (this.ws) {
      this.ws.close(1000, "Client disconnect")
      this.ws = null
    }
    this.setState("disconnected")
  }

  private handleMessage(message: { type: string; data: unknown }): void {
    const { type, data } = message
    
    if (type === "pong") {
      return
    }

    const callbacks = this.listeners.get(type)
    if (callbacks) {
      callbacks.forEach((callback) => callback(data))
    }

    const anyCallbacks = this.listeners.get("*")
    if (anyCallbacks) {
      anyCallbacks.forEach((callback) => callback(message))
    }
  }

  on(event: string, callback: EventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)

    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }

  off(event: string, callback: EventCallback): void {
    this.listeners.get(event)?.delete(callback)
  }

  send(type: string, data?: unknown): void {
    const message = { type, data }

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      this.messageQueue.push(message)
    }
  }

  private flushQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()
      if (message && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(message))
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached")
      return
    }

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    )

    console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1})`)

    setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  private startPing(): void {
    this.pingInterval = window.setInterval(() => {
      this.send("ping", { timestamp: Date.now() })
    }, 30000)
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  private setState(state: ConnectionState): void {
    this.state = state
    this.stateListeners.forEach((listener) => listener(state))
  }

  getState(): ConnectionState {
    return this.state
  }

  onStateChange(listener: (state: ConnectionState) => void): () => void {
    this.stateListeners.add(listener)
    return () => {
      this.stateListeners.delete(listener)
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws"

export const wsClient = new WebSocketClient(WS_URL)
