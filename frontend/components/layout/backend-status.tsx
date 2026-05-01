"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"

export function BackendStatus() {
  const [online, setOnline] = useState(false)
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const res = await fetch(`${base}/api/v1/health`, { signal: AbortSignal.timeout(3000) })
        if (!cancelled) setOnline(res.ok)
      } catch {
        if (!cancelled) setOnline(false)
      }
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
