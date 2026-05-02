"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { getToken } from "@/lib/auth"

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

    let sseUrl = url
    const token = getToken()
    if (token && !sseUrl.includes("token=")) {
      sseUrl += sseUrl.includes("?") ? "&" : "?"
      sseUrl += `token=${encodeURIComponent(token)}`
    }

    const es = new EventSource(sseUrl)
    sourceRef.current = es

    es.onopen = () => setIsConnected(true)

    es.addEventListener("progress", (e) => {
      addEvent({ type: "progress", data: parseEventData(e.data) })
    })

    es.addEventListener("partial", (e) => {
      addEvent({ type: "partial", data: parseEventData(e.data) })
    })

    es.addEventListener("generation_error", (e) => {
      const data = "data" in e && typeof e.data === "string" ? e.data : ""
      const parsed = data ? parseEventData(data) : { message: "生成失败，但后端没有返回具体错误" }
      if (typeof parsed === "object" && parsed && "message" in parsed) {
        setError(String(parsed.message))
      } else {
        setError("生成失败")
      }
      addEvent({ type: "error", data: parsed })
    })

    es.addEventListener("done", (e) => {
      setIsConnected(false)
      const data = "data" in e && typeof e.data === "string" ? e.data : ""
      const parsed = data ? parseEventData(data) : { message: "Done", status: "done" }
      addEvent({ type: "done", data: parsed })
      es.close()
      if (sourceRef.current === es) sourceRef.current = null
    })

    es.onerror = () => {
      if (sourceRef.current === es && !error) {
        setError("连接中断，可能是网络问题或生成超时，请重试")
      }
      setIsConnected(false)
    }
  }, [addEvent, disconnect, error])

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return { events, isConnected, error, connect, disconnect }
}
