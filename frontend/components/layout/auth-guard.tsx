"use client"

import { useRouter, usePathname } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { isAuthenticated, fetchMe, setUser } from "@/lib/auth"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [ready, setReady] = useState(false)
  const checkedRef = useRef(false)

  useEffect(() => {
    // 登录页免检查
    if (pathname === "/login") {
      setReady(true)
      return
    }

    // 仅首次认证检查，避免 pathname 变化时重复触发
    if (checkedRef.current) {
      // 后续路由变化只需验证 token 仍存在
      if (!isAuthenticated()) {
        router.replace("/login")
        return
      }
      return
    }

    if (!isAuthenticated()) {
      router.replace("/login")
      return
    }

    checkedRef.current = true

    fetchMe().then((user) => {
      if (!user) {
        router.replace("/login")
        return
      }
      setUser(user)
      setReady(true)
    })
  }, [pathname, router])

  if (pathname === "/login") return <>{children}</>

  if (!ready) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  return <>{children}</>
}
