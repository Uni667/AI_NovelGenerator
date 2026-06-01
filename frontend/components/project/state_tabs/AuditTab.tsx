import React, { useEffect, useState } from "react"
import { useProjectContext } from "../ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export function AuditTab() {
  const { projectId } = useProjectContext()
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const loadLogs = async () => {
    setLoading(true)
    try {
      const res = await api.client.get(`/api/v1/projects/${projectId}/state/audit-logs`)
      setLogs(res.data || [])
    } catch (err) {
      toast.error("加载审计日志失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [projectId])

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden h-full pt-2">
      <Card className="flex-1 flex flex-col overflow-hidden border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">状态审计日志 (Audit Logs)</CardTitle>
          <CardDescription>记录所有导致状态变化的编辑、合并与回滚操作</CardDescription>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto space-y-4">
          {loading ? (
            <div className="text-sm text-muted-foreground text-center py-10">加载中...</div>
          ) : logs.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-10">暂无审计日志</div>
          ) : (
            <div className="relative border-l border-border/50 ml-4 pl-6 space-y-6">
              {logs.map((log: any, idx: number) => (
                <div key={idx} className="relative">
                  <div className={`absolute -left-[31px] w-4 h-4 rounded-full border-2 border-background ${
                    log.risk_level === 'high' ? 'bg-red-500' :
                    log.event_type.includes('fail') || log.event_type.includes('reject') ? 'bg-amber-500' :
                    'bg-blue-500'
                  }`}></div>
                  <div className="bg-muted/30 border rounded-lg p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-semibold text-sm">
                        {log.event_type} <span className="text-muted-foreground font-normal">on</span> {log.file}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(log.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="text-sm text-foreground mb-2">
                      <strong>原因:</strong> {log.reason || '无'}
                    </div>
                    <div className="flex gap-2 text-xs text-muted-foreground flex-wrap">
                      <Badge variant="outline">{log.entity_type}: {log.entity_id}</Badge>
                      {log.risk_level === 'high' && <Badge variant="outline" className="text-red-500 border-red-500/50">HIGH RISK</Badge>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
