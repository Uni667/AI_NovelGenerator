"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { TriangleAlert, RotateCw } from "lucide-react"

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center space-y-4 max-w-sm">
        <TriangleAlert className="h-12 w-12 text-destructive mx-auto" />
        <h2 className="text-lg font-semibold">出了点问题</h2>
        <p className="text-sm text-muted-foreground">{error.message || "发生未知错误，请稍后重试"}</p>
        <Button onClick={reset} variant="outline" className="gap-2">
          <RotateCw className="h-4 w-4" />
          重试
        </Button>
      </div>
    </div>
  )
}
