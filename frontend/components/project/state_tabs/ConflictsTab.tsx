import React, { useState } from "react"
import { useProjectContext } from "../ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Info, Bot } from "lucide-react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export function ConflictsTab() {
  const { projectId } = useProjectContext()
  const [conflicts, setConflicts] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [hasScanned, setHasScanned] = useState(false)

  const scanConflicts = async (enableAi: boolean = false) => {
    if (enableAi) setAiLoading(true)
    else setLoading(true)
    
    try {
      const res = await api.client.get(`/api/v1/projects/${projectId}/state/conflicts?enable_ai=${enableAi}`)
      setConflicts(res.data?.conflicts || [])
      setHasScanned(true)
      toast.success(enableAi ? "AI 深度检测完成" : "规则检测完成")
    } catch (err) {
      toast.error("冲突检测失败")
    } finally {
      setLoading(false)
      setAiLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden h-full pt-2">
      <div className="flex gap-4 items-center mb-2">
        <Button onClick={() => scanConflicts(false)} disabled={loading || aiLoading}>
          {loading ? "检测中..." : "检测状态冲突"}
        </Button>
        <Button variant="outline" onClick={() => scanConflicts(true)} disabled={loading || aiLoading} className="text-amber-600 border-amber-500/50 hover:bg-amber-500/10">
          <Bot className="w-4 h-4 mr-2" />
          {aiLoading ? "AI 思考中..." : "AI 辅助深度检测"}
        </Button>
        <span className="text-xs text-muted-foreground ml-auto">
          提示：冲突检测只提示，不会自动修复。
        </span>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">冲突列表 (Conflicts)</CardTitle>
          <CardDescription>内存状态文件之间的逻辑断层或设置矛盾</CardDescription>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto space-y-4">
          {!hasScanned && (
            <div className="text-center text-muted-foreground py-10 text-sm">
              点击上方按钮开始检测冲突
            </div>
          )}
          
          {hasScanned && conflicts.length === 0 && (
            <div className="text-center text-emerald-500 py-10 text-sm flex flex-col items-center gap-2">
              <span className="text-4xl">🎉</span>
              未检测到任何逻辑冲突，状态十分健康！
            </div>
          )}

          {conflicts.map(c => (
            <div key={c.conflict_id} className={`border rounded-lg p-4 ${
              c.risk_level === 'high' ? 'border-red-500/50 bg-red-500/5' :
              c.risk_level === 'medium' ? 'border-amber-500/50 bg-amber-500/5' :
              'border-muted bg-muted/30'
            }`}>
              <div className="flex justify-between items-start mb-2">
                <div className="font-bold flex items-center gap-2">
                  {c.risk_level === 'high' ? <AlertTriangle className="w-4 h-4 text-red-500" /> : <Info className="w-4 h-4 text-amber-500" />}
                  {c.title}
                </div>
                <Badge variant="outline" className={`
                  ${c.risk_level === 'high' ? 'text-red-500 border-red-500/50' : 
                    c.risk_level === 'medium' ? 'text-amber-500 border-amber-500/50' : ''}
                `}>
                  {c.risk_level.toUpperCase()} RISK
                </Badge>
              </div>
              <div className="text-sm mb-3 text-muted-foreground">
                {c.description}
              </div>
              <div className="text-xs text-muted-foreground mb-3">
                <strong>涉及文件:</strong> {c.related_files?.join(", ")}
              </div>
              
              {c.suggested_actions?.length > 0 && (
                <div className="border-t border-border/50 pt-3 mt-3">
                  <div className="text-xs font-semibold mb-2">修复建议 (需去对应 Tab 手动修改):</div>
                  <div className="flex gap-2 flex-wrap">
                    {c.suggested_actions.map((act: any, i: number) => (
                      <Badge key={i} variant="secondary">{act.label}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
