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
        clearToken()
        router.replace("/login")
        return
      }
      setUser(user)
      setReady(true)
    } catch {
      setReady(true)
    }
  }, [pathname, router])

  useEffect(() => {
    void checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (ready && pathname !== "/login" && !isAuthenticated()) {
      router.replace("/login")
    }
  }, [pathname, ready, router])

  if (pathname === "/login") return <>{children}</>

  if (!ready) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!isAuthenticated()) return null

  return <>{children}</>
}
