"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"

export function BackendStatus() {
  const [online, setOnline] = useState(false)
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

  useEffect(() => {
    let cancelled = false
    const checkOnce = async (): Promise<boolean> => {
      try {
        const res = await fetch(`${base}/api/v1/health`, { signal: AbortSignal.timeout(8000) })
        return res.ok
      } catch {
        return false
      }
    }
    const check = async () => {
      const ok = await checkOnce()
      if (cancelled) return
      if (ok) {
        setOnline(true)
        return
      }
      // 冷启动重试：等 2s 再试一次
      await new Promise(r => setTimeout(r, 2000))
      if (cancelled) return
      const retry = await checkOnce()
      if (!cancelled) setOnline(retry)
    }
    check()
    const interval = setInterval(check, 15000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [base])

  return (
    <Badge variant={online ? "default" : "secondary"} className="gap-1 text-xs cursor-default">
      {online ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
      <span className="hidden sm:inline">{online ? "后端在线" : "后端离线"}</span>
    </Badge>
  )
}
