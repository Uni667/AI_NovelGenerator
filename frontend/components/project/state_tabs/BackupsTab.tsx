import React, { useEffect, useState } from "react"
import { useProjectContext } from "../ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { RotateCcw } from "lucide-react"

export function BackupsTab() {
  const { projectId } = useProjectContext()
  const [backups, setBackups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [restoreId, setRestoreId] = useState<string | null>(null)
  const [reason, setReason] = useState("")

  const loadBackups = async () => {
    setLoading(true)
    try {
      const res = await api.client.get(`/api/v1/projects/${projectId}/state/backups`)
      setBackups(res.data || [])
    } catch (err) {
      toast.error("加载备份列表失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBackups()
  }, [projectId])

  const handleRestore = async () => {
    if (!reason.trim()) {
      toast.error("请填写回滚原因")
      return
    }
    try {
      await api.client.post(`/api/v1/projects/${projectId}/state/backups/${restoreId}/restore`, { reason })
      toast.success("备份回滚成功")
      setRestoreId(null)
      setReason("")
      loadBackups()
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || err.response?.data?.detail || "回滚失败")
    }
  }

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden h-full pt-2">
      <Card className="flex-1 flex flex-col overflow-hidden border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">状态备份与回滚 (Backups)</CardTitle>
          <CardDescription>每次编辑或应用大纲演化前，系统会自动为您备份原状态文件</CardDescription>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto space-y-4">
          {loading ? (
            <div className="text-sm text-muted-foreground text-center py-10">加载中...</div>
          ) : backups.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-10">暂无备份文件</div>
          ) : (
            <div className="grid gap-3">
              {backups.map(b => (
                <div key={b.backup_id} className="border rounded-md p-3 flex justify-between items-center bg-muted/20">
                  <div>
                    <div className="font-semibold text-sm mb-1">{b.backup_id}</div>
                    <div className="text-xs text-muted-foreground">备份时间: {new Date(b.created_at).toLocaleString()}</div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setRestoreId(b.backup_id)} className="text-red-500 hover:text-red-600 hover:bg-red-500/10 border-red-500/30">
                    <RotateCcw className="w-3 h-3 mr-1" /> 回滚
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!restoreId} onOpenChange={(open) => !open && setRestoreId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-500 flex items-center gap-2">
              <RotateCcw className="w-5 h-5" /> 确认回滚备份？
            </DialogTitle>
            <DialogDescription>
              你即将恢复文件 <strong>{restoreId}</strong>。这会覆盖当前对应的状态文件，并影响未来生成。
              恢复前系统会自动备份当前状态。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">请填写回滚原因（必填）:</label>
              <Input 
                value={reason} 
                onChange={e => setReason(e.target.value)}
                placeholder="例如：AI把十四叔本名改错了，我需要回滚"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreId(null)}>取消</Button>
            <Button variant="destructive" onClick={handleRestore}>确认覆盖</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
