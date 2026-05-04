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
    return { message: "连接被中断，未能解析服务端返回。" }
  }
}

function formatTerminalError(payload: any): string {
  if (!payload || typeof payload !== "object") return "生成失败，请稍后重试。"
  if (payload.message) return String(payload.message)

  const category = String(payload.error_category || "")
  switch (category) {
    case "config_missing":
      return "模型配置缺失或无效，请检查模型名称、Base URL 和 API Key。"
    case "auth_failed":
      return "模型服务认证失败，请检查 API Key 或账号权限。"
    case "network_error":
      return "无法连接到模型服务，请检查网络、Base URL 或代理设置。"
    case "timeout":
      return "模型服务响应超时，请稍后重试。"
    case "provider_4xx":
      return "模型服务拒绝了当前请求，请检查模型配置和请求参数。"
    case "provider_5xx":
      return "模型服务暂时异常，请稍后重试。"
    case "stream_interrupted":
      return "模型服务传输过程中断，请重新发起生成。"
    case "parse_failure":
      return "模型返回内容解析失败，请稍后重试。"
    default:
      return "生成失败，请查看后端日志获取更多信息。"
  }
}

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const connectionSeqRef = useRef(0)
  const errorRef = useRef<string | null>(null)
  const doneReceivedRef = useRef(false)

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

  const connect = useCallback(
    (url: string) => {
      disconnect()
      setEvents([])
      setError(null)
      errorRef.current = null
      doneReceivedRef.current = false
      connectionSeqRef.current += 1
      const connectionId = connectionSeqRef.current

      let sseUrl = url
      const token = getToken()
      if (token && !sseUrl.includes("token=")) {
        sseUrl += sseUrl.includes("?") ? "&" : "?"
        sseUrl += `token=${encodeURIComponent(token)}`
      }

      const es = new EventSource(sseUrl)
      sourceRef.current = es

      const isActiveConnection = () =>
        sourceRef.current === es && connectionSeqRef.current === connectionId

      es.onopen = () => {
        if (!isActiveConnection()) return
        setIsConnected(true)
      }

      es.addEventListener("progress", (e) => {
        if (!isActiveConnection()) return
        addEvent({ type: "progress", data: parseEventData(e.data) })
      })

      es.addEventListener("partial", (e) => {
        if (!isActiveConnection()) return
        addEvent({ type: "partial", data: parseEventData(e.data) })
      })

      es.addEventListener("generation_error", (e) => {
        if (!isActiveConnection()) return
        const parsed =
          "data" in e && typeof e.data === "string"
            ? parseEventData(e.data)
            : { message: "生成失败，但后端没有返回具体错误。" }
        const message = formatTerminalError(parsed)
        setError(message)
        errorRef.current = message
        const errorData = (
          parsed && typeof parsed === "object"
            ? { ...(parsed as Record<string, unknown>), message }
            : { message }
        ) as any
        addEvent({ type: "error", data: errorData })
        if (
          parsed &&
          typeof parsed === "object" &&
          (parsed as Record<string, unknown>).terminal
        ) {
          setIsConnected(false)
          es.close()
          if (sourceRef.current === es) sourceRef.current = null
        }
      })

      es.addEventListener("done", (e) => {
        if (!isActiveConnection()) return
        doneReceivedRef.current = true
        setIsConnected(false)
        const parsed =
          "data" in e && typeof e.data === "string"
            ? parseEventData(e.data)
            : { message: "Done", status: "done" }
        addEvent({ type: "done", data: parsed })
        es.close()
        if (sourceRef.current === es) sourceRef.current = null
      })

      es.addEventListener("cancelled", (e) => {
        if (!isActiveConnection()) return
        doneReceivedRef.current = true
        setIsConnected(false)
        const parsed =
          "data" in e && typeof e.data === "string"
            ? parseEventData(e.data)
            : { message: "任务已取消", status: "cancelled" }
        addEvent({ type: "cancelled", data: parsed })
        es.close()
        if (sourceRef.current === es) sourceRef.current = null
      })

      es.onerror = () => {
        if (!isActiveConnection()) return
        // 如果已经收到 done/cancelled 事件, onerror 是正常的连接关闭,不报错
        if (doneReceivedRef.current) {
          setIsConnected(false)
          es.close()
          if (sourceRef.current === es) sourceRef.current = null
          return
        }
        const message =
          errorRef.current ||
          "生成连接已中断，请检查后端服务或模型服务连通性。"
        setError(message)
        errorRef.current = message
        addEvent({
          type: "error",
          data: { message, status: "failed", terminal: true },
        })
        setIsConnected(false)
        es.close()
        if (sourceRef.current === es) sourceRef.current = null
      }
    },
    [addEvent, disconnect],
  )

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return { events, isConnected, error, connect, disconnect }
}
