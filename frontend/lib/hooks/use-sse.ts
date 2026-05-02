"use client"

import { useCallback, useEffect, useRef, useState } from "react"

const MAX_EVENTS = 500

interface SSEEvent {
  type: string
  data: any
}

function parseEventData(data: string) {
  try {
    return JSON.parse(data) as unknown
  } catch {
    return { message: "Connection interrupted" }
  }
}

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)

  const addEvent = useCallback((event: SSEEvent) => {
    setEvents((prev) => {
      const next = [...prev, event]
      return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next
    })
  }, [])

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
    setIsConnected(false)
  }, [])

  const connect = useCallback((url: string) => {
    disconnect()
    setEvents([])
    setError(null)

    const es = new EventSource(url)
    sourceRef.current = es

    es.onopen = () => setIsConnected(true)

    es.addEventListener("progress", (e) => {
      addEvent({ type: "progress", data: parseEventData(e.data) })
    })

    es.addEventListener("partial", (e) => {
      addEvent({ type: "partial", data: parseEventData(e.data) })
    })

    es.addEventListener("error", (e) => {
      const data = "data" in e && typeof e.data === "string" ? e.data : ""
      const parsed = data ? parseEventData(data) : { message: "Connection interrupted" }
      if (typeof parsed === "object" && parsed && "message" in parsed) {
        setError(String(parsed.message))
      } else {
        setError("Connection interrupted")
      }
      addEvent({ type: "error", data: parsed })
    })

    es.addEventListener("done", () => {
      setIsConnected(false)
      addEvent({ type: "done", data: { message: "Done" } })
      es.close()
      if (sourceRef.current === es) sourceRef.current = null
    })

    es.onerror = () => {
      setIsConnected(false)
    }
  }, [addEvent, disconnect])

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return { events, isConnected, error, connect, disconnect }
}
