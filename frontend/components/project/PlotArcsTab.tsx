"use client"

import { useState, useEffect } from "react"
import { useProjectContext } from "./ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Loader2, Save, BookOpen } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api-client"

export function PlotArcsTab() {
  const { projectId } = useProjectContext()
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchPlotArcs = async () => {
      setLoading(true)
      try {
        const data = await api.plotArcs.get(projectId)
        setContent(data.content)
      } catch (error: any) {
        toast.error(error.message || "加载伏笔暗线台账失败")
      } finally {
        setLoading(false)
      }
    }
    
    if (projectId) {
      fetchPlotArcs()
    }
  }, [projectId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.plotArcs.update(projectId, content)
      toast.success("伏笔暗线台账已更新")
    } catch (error: any) {
      toast.error(error.message || "保存失败")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="space-y-1">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-primary" />
              伏笔暗线台账
            </CardTitle>
            <CardDescription>
              全局管理小说中埋下的伏笔与暗线。此文件会被大模型读取并在续写时作为参考。
            </CardDescription>
          </div>
          <Button onClick={handleSave} disabled={loading || saving} className="shadow-md">
            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            保存修改
          </Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-[60vh] items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary/50" />
            </div>
          ) : (
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="min-h-[60vh] font-mono text-sm leading-relaxed p-4 bg-background/50 focus:bg-background/80 resize-y rounded-xl border-border/50"
              placeholder="在此输入伏笔暗线..."
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
