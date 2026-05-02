"use client"

import { useRouter, usePathname } from "next/navigation"
import { useEffect, useState, useCallback } from "react"
import { isAuthenticated, fetchMe, setUser, clearToken } from "@/lib/auth"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [ready, setReady] = useState(false)

  const checkAuth = useCallback(async () => {
    if (pathname === "/login") {
      setReady(true)
      return
    }
    if (!isAuthenticated()) {
      router.replace("/login")
      return
    }
    try {
      const user = await fetchMe()
      if (!user) {
        // token 无效，清除并跳转
        clearToken()
        router.replace("/login")
        return
      }
      setUser(user)
      setReady(true)
    } catch {
      // 网络错误等不回跳，等用户重试
      setReady(true)
    }
  }, [pathname, router])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  if (pathname === "/login") return <>{children}</>

  if (!ready) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  // 渲染后如发现 token 被清除（api-client 401 触发），跳登录
  if (!isAuthenticated()) {
    if (typeof window !== "undefined") {
      window.location.href = "/login"
    }
    return null
  }

  return <>{children}</>
}
