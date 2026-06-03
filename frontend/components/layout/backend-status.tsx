"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"
import { healthService } from "@/lib/services/healthService"

const CHECK_INTERVAL = 15000

export function BackendStatus() {
  const [online, setOnline] = useState(true)
  const [checkedAt, setCheckedAt] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const check = async () => {
      const status = await healthService.checkBackendHealth()
      if (cancelled) return
      setOnline(status.online)
      setCheckedAt(status.checkedAt)
    }

    const initialTimer = setTimeout(check, 2000)
    const interval = setInterval(check, CHECK_INTERVAL)
    return () => { cancelled = true; clearTimeout(initialTimer); clearInterval(interval) }
  }, [])

  return (
    <Badge 
      variant="outline" 
      className={`gap-1.5 text-[10px] font-mono px-2 py-0.5 border cursor-default transition-colors duration-500 ${
        online 
          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" 
          : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
      }`}
    >
      {online ? <Wifi className="h-3 w-3 animate-pulse" /> : <WifiOff className="h-3 w-3 text-rose-600 dark:text-rose-400" />}
      <span>{online ? "后端在线" : `后端离线${checkedAt ? ` (最后检测: ${checkedAt})` : ""}`}</span>
    </Badge>
  )
}
