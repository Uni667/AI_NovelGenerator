import { useState, useEffect, useCallback } from "react"
import { Play, Pause, Square, AlertTriangle, CheckCircle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { toast } from "sonner"
import { api } from "@/lib/api-client"

interface AbsorptionProgressPanelProps {
  bookId: string
  bookStatus: string
  onStatusChange: () => void
}

export function AbsorptionProgressPanel({ bookId, bookStatus, onStatusChange }: AbsorptionProgressPanelProps) {
  const [taskState, setTaskState] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  const isAbsorbing = bookStatus === "absorbing"
  
  const loadStatus = useCallback(async () => {
    if (!isAbsorbing) {
      setTaskState(null)
      return
    }
    
    setLoading(true)
    try {
      const res = await api.localLibrary.getAbsorptionStatus(bookId)
      setTaskState(res)
      if (res && res.status === "completed") {
        onStatusChange()
      } else if (res && res.status === "failed") {
        onStatusChange()
      }
    } catch (e) {
      // ignore or log
    } finally {
      setLoading(false)
    }
  }, [bookId, isAbsorbing, onStatusChange])

  useEffect(() => {
    loadStatus()
    let interval: NodeJS.Timeout
    if (isAbsorbing) {
      interval = setInterval(loadStatus, 2000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [loadStatus, isAbsorbing])

  const handleStart = async () => {
    setActionLoading(true)
    try {
      await api.localLibrary.absorb(bookId)
      toast.success("吸收任务已启动")
      onStatusChange()
    } catch (e: any) {
      toast.error(e?.message || "启动失败")
    } finally {
      setActionLoading(false)
    }
  }

  const handlePause = async () => {
    setActionLoading(true)
    try {
      await api.localLibrary.pauseAbsorb(bookId)
      toast.success("已请求暂停")
      await loadStatus()
    } catch (e: any) {
      toast.error(e?.message || "暂停失败")
    } finally {
      setActionLoading(false)
    }
  }

  const handleResume = async () => {
    setActionLoading(true)
    try {
      await api.localLibrary.resumeAbsorb(bookId)
      toast.success("已请求恢复")
      await loadStatus()
    } catch (e: any) {
      toast.error(e?.message || "恢复失败")
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!window.confirm("确定要取消吸收任务吗？进度可能丢失。")) return
    setActionLoading(true)
    try {
      await api.localLibrary.cancelAbsorb(bookId)
      toast.success("已取消任务")
      onStatusChange()
    } catch (e: any) {
      toast.error(e?.message || "取消失败")
    } finally {
      setActionLoading(false)
    }
  }

  if (!isAbsorbing && bookStatus !== "error") {
    return (
      <div className="bg-background/50 border border-border/50 rounded-xl p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {bookStatus === "absorbed" ? "本书已完成吸收" : "尚未开始吸收转换流程"}
          </div>
          <Button onClick={handleStart} disabled={actionLoading} className="shadow-glow">
            <Play className="w-4 h-4 mr-2" />
            {bookStatus === "absorbed" ? "重新吸收" : "开始全书吸收"}
          </Button>
        </div>
      </div>
    )
  }

  if (!taskState) {
    return (
      <div className="flex items-center justify-center p-4 text-sm text-muted-foreground">
        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
        正在获取任务状态...
      </div>
    )
  }

  const pct = Math.round((taskState.progress_current / Math.max(1, taskState.progress_total)) * 100) || 0

  return (
    <div className="bg-background/80 border border-border/60 rounded-xl p-5 space-y-4 relative overflow-hidden">
      {/* Background progress bar hint */}
      <div 
        className="absolute left-0 top-0 bottom-0 bg-primary/5 transition-all duration-500 ease-in-out" 
        style={{ width: `${pct}%` }} 
      />
      
      <div className="relative z-10 flex items-center justify-between">
        <div>
          <div className="font-medium flex items-center gap-2">
            任务进度: {pct}%
            {taskState.status === "running" && <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />}
            {taskState.status === "paused" && <span className="flex h-2 w-2 rounded-full bg-amber-500" />}
            {taskState.status === "failed" && <span className="flex h-2 w-2 rounded-full bg-destructive" />}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            当前步骤: {taskState.current_step || "初始化..."}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-1">
            状态
          </div>
          <div className="text-sm">
            {taskState.status === "running" && "执行中"}
            {taskState.status === "paused" && "已暂停"}
            {taskState.status === "cancelling" && "正在取消..."}
            {taskState.status === "cancelled" && "已取消"}
            {taskState.status === "failed" && <span className="text-destructive">失败</span>}
            {taskState.status === "completed" && <span className="text-green-500">已完成</span>}
          </div>
        </div>
      </div>

      <Progress value={pct} className="h-2 relative z-10" />

      {taskState.error_message && (
        <div className="bg-destructive/10 text-destructive text-xs p-3 rounded flex items-start gap-2 relative z-10">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="break-all">{taskState.error_message}</div>
        </div>
      )}

      <div className="flex items-center gap-2 pt-2 relative z-10">
        {taskState.status === "running" && (
          <Button variant="outline" size="sm" onClick={handlePause} disabled={actionLoading}>
            <Pause className="w-4 h-4 mr-2" />
            暂停
          </Button>
        )}
        {taskState.status === "paused" && (
          <Button variant="outline" size="sm" onClick={handleResume} disabled={actionLoading}>
            <Play className="w-4 h-4 mr-2" />
            恢复
          </Button>
        )}
        {['running', 'paused', 'failed'].includes(taskState.status) && (
          <Button variant="destructive" size="sm" onClick={handleCancel} disabled={actionLoading}>
            <Square className="w-4 h-4 mr-2" />
            取消
          </Button>
        )}
        {taskState.status === "failed" && (
          <Button variant="default" size="sm" onClick={handleStart} disabled={actionLoading}>
            <RefreshCw className="w-4 h-4 mr-2" />
            重试
          </Button>
        )}
      </div>
    </div>
  )
}
