"use client"

import { useEffect, useRef, useState, useCallback } from "react"

const MAX_EVENTS = 500

interface SSEEvent {
  type: string
  data: any
}

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)

  const addEvent = useCallback((event: SSEEvent) => {
    setEvents(prev => {
      const next = [...prev, event]
      return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next
    })
  }, [])

  const connect = useCallback((url: string) => {
    disconnect()
    setEvents([])
    setError(null)

    const es = new EventSource(url)
    sourceRef.current = es

    es.onopen = () => setIsConnected(true)

    es.addEventListener("progress", (e) => {
      addEvent({ type: "progress", data: JSON.parse(e.data) })
    })

    es.addEventListener("partial", (e) => {
      addEvent({ type: "partial", data: JSON.parse(e.data) })
    })

    es.addEventListener("error", (e: any) => {
      if (e.data) {
        try { setError(JSON.parse(e.data).message || "未知错误") }
        catch { setError("连接中断") }
      }
      addEvent({ type: "error", data: e.data ? (() => { try { return JSON.parse(e.data) } catch { return { message: "连接中断" } } })() : { message: "连接中断" } })
    })

    es.addEventListener("done", () => {
      setIsConnected(false)
      addEvent({ type: "done", data: { message: "完成" } })
      es.close()
    })

    es.onerror = () => {
      setIsConnected(false)
    }
  }, [addEvent])

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
