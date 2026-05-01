"use client"

import { useEffect, useRef, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"

const API_BASE = "https://ai-novel-backend-production.up.railway.app"

export function BackendStatus() {
  const [online, setOnline] = useState(false)
  const failCount = useRef(0)

  useEffect(() => {
    let cancelled = false

    const doFetch = async (): Promise<boolean> => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(8000) })
        return res.ok
      } catch {
        return false
      }
    }

    const check = async () => {
      let ok = await doFetch()
      if (!ok && !cancelled) {
        await new Promise(r => setTimeout(r, 2000))
        if (!cancelled) ok = await doFetch()
      }
      if (cancelled) return
      if (ok) {
        failCount.current = 0
        setOnline(true)
      } else {
        failCount.current++
        // 连续失败 3 次才显示离线（避免偶发网络波动导致闪烁）
        if (failCount.current >= 3) setOnline(false)
      }
    }

    check()
    const interval = setInterval(check, 15000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [API_BASE])

  return (
    <Badge variant={online ? "default" : "secondary"} className="gap-1 text-xs cursor-default">
      {online ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
      <span className="hidden sm:inline">{online ? "后端在线" : "后端离线"}</span>
    </Badge>
  )
}
