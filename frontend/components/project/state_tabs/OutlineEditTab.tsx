import React, { useState, useEffect } from "react"
import { useProjectContext } from "../ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Lock, Save } from "lucide-react"

export function OutlineEditTab({ stateData, loadData }: any) {
  const { projectId } = useProjectContext()
  const chapters = stateData?.outline_state?.chapters || []
  
  const [selectedIndex, setSelectedIndex] = useState<number | null>(chapters[0]?.chapter_index || null)
  const [formData, setFormData] = useState<any>({})
  const [reason, setReason] = useState("")
  
  const selectedChapter = chapters.find((x: any) => x.chapter_index === selectedIndex)
  const isEditable = selectedChapter && selectedChapter.status === "planned" && !selectedChapter.locked

  useEffect(() => {
    if (selectedChapter) {
      setFormData({
        title: selectedChapter.title || "",
        planned_summary: selectedChapter.planned_summary || "",
        chapter_goal: selectedChapter.chapter_goal || "",
        key_events: selectedChapter.key_events || "",
        foreshadowing: selectedChapter.foreshadowing || "",
        notes: selectedChapter.notes || ""
      })
    }
  }, [selectedIndex, chapters])

  const handleSave = async () => {
    if (!reason.trim()) return toast.error("请输入修改原因")
    if (!isEditable) return toast.error("当前章节不可编辑")
    
    try {
      await api.client.patch(`/api/v1/projects/${projectId}/state/outline/chapters/${selectedIndex}`, {
        updates: formData, reason, confirm_high_risk: false
      })
      toast.success(`第 ${selectedIndex} 章更新成功`)
      setReason("")
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || "更新失败")
    }
  }

  return (
    <div className="flex h-full gap-4 pt-2">
      <div className="w-48 flex flex-col gap-2 overflow-y-auto border-r pr-2">
        {chapters.map((ch: any) => (
          <Button 
            key={ch.chapter_index} 
            variant={selectedIndex === ch.chapter_index ? "default" : "ghost"} 
            className="justify-start truncate"
            onClick={() => setSelectedIndex(ch.chapter_index)}
          >
            {ch.status !== "planned" || ch.locked ? <Lock className="w-3 h-3 mr-2 text-muted-foreground" /> : null}
            第 {ch.chapter_index} 章: {ch.title || '无标题'}
          </Button>
        ))}
      </div>
      
      {selectedChapter ? (
        <Card className="flex-1 flex flex-col overflow-hidden border-border/50">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="text-lg flex justify-between items-center">
              <span>编辑大纲规划: 第 {selectedIndex} 章</span>
              <Button onClick={handleSave} size="sm" disabled={!isEditable}>
                <Save className="w-4 h-4 mr-1"/> 保存修改
              </Button>
            </CardTitle>
            <CardDescription>
              {isEditable ? "编辑未来章节规划" : "当前章节已定稿或被锁定，无法进行基础编辑"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>章节标题</Label>
                <Input disabled={!isEditable} value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} />
              </div>
              <div className="space-y-2">
                <Label>计划内容 (Planned Summary)</Label>
                <Textarea disabled={!isEditable} value={formData.planned_summary} onChange={e => setFormData({...formData, planned_summary: e.target.value})} rows={4} />
              </div>
              <div className="space-y-2">
                <Label>核心目标 (Chapter Goal)</Label>
                <Input disabled={!isEditable} value={formData.chapter_goal} onChange={e => setFormData({...formData, chapter_goal: e.target.value})} />
              </div>
              <div className="space-y-2">
                <Label>伏笔与线索 (Foreshadowing)</Label>
                <Input disabled={!isEditable} value={formData.foreshadowing} onChange={e => setFormData({...formData, foreshadowing: e.target.value})} />
              </div>
            </div>
            
            <div className="border-t pt-4 space-y-4 mt-6">
              <div className="space-y-2">
                <Label className="text-red-500 font-bold">* 修改原因 (必填)</Label>
                <Input disabled={!isEditable} value={reason} onChange={e => setReason(e.target.value)} placeholder="请说明修改该章大纲的原因..." />
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
          请选择一个章节
        </div>
      )}
    </div>
  )
}
