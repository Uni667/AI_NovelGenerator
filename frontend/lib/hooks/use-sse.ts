"use client"

import { useEffect, useRef, useState, useCallback } from "react"

interface SSEEvent {
  type: string
  data: any
}

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback((url: string) => {
    disconnect()
    setEvents([])
    setError(null)

    // SSE doesn't support POST natively, use fetch + ReadableStream for POST SSE
    const es = new EventSource(url)
    sourceRef.current = es

    es.onopen = () => setIsConnected(true)

    es.addEventListener("progress", (e) => {
      setEvents(prev => [...prev, { type: "progress", data: JSON.parse(e.data) }])
    })

    es.addEventListener("partial", (e) => {
      setEvents(prev => [...prev, { type: "partial", data: JSON.parse(e.data) }])
    })

    es.addEventListener("error", (e: any) => {
      if (e.data) {
        setError(JSON.parse(e.data).message || "未知错误")
      }
      setEvents(prev => [...prev, { type: "error", data: e.data ? JSON.parse(e.data) : { message: "连接中断" } }])
    })

    es.addEventListener("done", () => {
      setIsConnected(false)
      setEvents(prev => [...prev, { type: "done", data: { message: "完成" } }])
      es.close()
    })

    es.onerror = () => {
      setIsConnected(false)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
    setIsConnected(false)
  }, [])

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return { events, isConnected, error, connect, disconnect }
}
