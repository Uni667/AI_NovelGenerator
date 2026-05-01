"use client"

import { useRouter, usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { isAuthenticated, fetchMe, setUser } from "@/lib/auth"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (pathname === "/login") {
      setReady(true)
      return
    }
    if (!isAuthenticated()) {
      router.replace("/login")
      return
    }
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
