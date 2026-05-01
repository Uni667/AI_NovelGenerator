"use client"

import { useEffect, useRef, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"

const API_BASE = "https://ai-novel-backend-production.up.railway.app"
const CHECK_INTERVAL = 30000

export function BackendStatus() {
  const [online, setOnline] = useState(true) // 默认乐观：在线
  const failCount = useRef(0)

  useEffect(() => {
    let cancelled = false

    const doFetch = async (): Promise<boolean> => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(10000) })
        return res.ok
      } catch {
        return false
      }
    }

    const check = async () => {
      let ok = await doFetch()
      if (!ok && !cancelled) {
        await new Promise(r => setTimeout(r, 3000))
        if (!cancelled) ok = await doFetch()
      }
      if (cancelled) return
      if (ok) {
        failCount.current = 0
        if (!cancelled) setOnline(true)
      } else {
        failCount.current++
        if (failCount.current >= 5 && !cancelled) setOnline(false)
      }
    }

    // 首次延迟 5 秒再检查，避免页面加载时触发 Railway 冷启动
    const initialTimer = setTimeout(check, 5000)
    const interval = setInterval(check, CHECK_INTERVAL)
    return () => { cancelled = true; clearTimeout(initialTimer); clearInterval(interval) }
  }, [])

  return (
    <Badge variant={online ? "default" : "secondary"} className="gap-1 text-xs cursor-default">
      {online ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
      <span className="hidden sm:inline">{online ? "后端在线" : "后端离线"}</span>
    </Badge>
  )
}
