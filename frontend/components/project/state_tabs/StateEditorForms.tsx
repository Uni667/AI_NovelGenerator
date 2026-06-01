import React, { useState, useEffect } from "react"
import { useProjectContext } from "../ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { AlertTriangle, Save } from "lucide-react"

// A generic wrapper for state editing forms
function EditFormWrapper({ title, description, reason, setReason, confirmHighRisk, setConfirmHighRisk, onSave, children, isHighRisk = false }: any) {
  return (
    <Card className="flex-1 flex flex-col overflow-hidden border-border/50">
      <CardHeader className="pb-3 border-b">
        <CardTitle className="text-lg flex justify-between items-center">
          <span>{title}</span>
          <Button onClick={onSave} size="sm"><Save className="w-4 h-4 mr-1"/> 保存修改</Button>
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-4">
          {children}
        </div>
        
        <div className="border-t pt-4 space-y-4 mt-6">
          <div className="space-y-2">
            <Label className="text-red-500 font-bold">* 修改原因 (必填)</Label>
            <Input value={reason} onChange={e => setReason(e.target.value)} placeholder="请详细说明为什么要手动修改状态..." />
          </div>
          
          {isHighRisk && (
            <div className="flex items-center space-x-2 bg-red-500/10 p-3 rounded-md border border-red-500/20">
              <Switch id="high-risk" checked={confirmHighRisk} onCheckedChange={setConfirmHighRisk} />
              <Label htmlFor="high-risk" className="text-red-500 flex items-center cursor-pointer">
                <AlertTriangle className="w-4 h-4 mr-1" />
                我确认执行此高风险操作 (涉及核心设定、生死、秘密揭露等，将影响全局)
              </Label>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function CharactersEditTab({ stateData, loadData }: any) {
  const { projectId } = useProjectContext()
  const characters = stateData?.character_state?.characters || []
  
  const [selectedId, setSelectedId] = useState(characters[0]?.id || "")
  const [formData, setFormData] = useState<any>({})
  const [reason, setReason] = useState("")
  const [confirmHighRisk, setConfirmHighRisk] = useState(false)
  
  useEffect(() => {
    const ch = characters.find((c: any) => c.id === selectedId)
    if (ch) {
      setFormData({
        true_name: ch.true_name || "",
        true_name_revealed_to_reader: !!ch.true_name_revealed_to_reader,
        true_name_revealed_to_characters: (ch.true_name_revealed_to_characters || []).join(", "),
        current_status: ch.current_status || ""
      })
    }
  }, [selectedId, characters])

  const handleSave = async () => {
    if (!reason.trim()) return toast.error("请输入修改原因")
    try {
      const updates = {
        true_name: formData.true_name,
        true_name_revealed_to_reader: formData.true_name_revealed_to_reader,
        true_name_revealed_to_characters: formData.true_name_revealed_to_characters.split(",").map((s:string) => s.trim()).filter(Boolean),
        current_status: formData.current_status
      }
      await api.client.patch(`/api/v1/projects/${projectId}/state/characters/${selectedId}`, {
        updates, reason, confirm_high_risk: confirmHighRisk
      })
      toast.success("人物状态更新成功")
      setReason(""); setConfirmHighRisk(false)
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || "更新失败")
    }
  }

  return (
    <div className="flex h-full gap-4 pt-2">
      <div className="w-48 flex flex-col gap-2 overflow-y-auto border-r pr-2">
        {characters.map((ch: any) => (
          <Button 
            key={ch.id} 
            variant={selectedId === ch.id ? "default" : "ghost"} 
            className="justify-start"
            onClick={() => setSelectedId(ch.id)}
          >
            {ch.display_name || ch.id}
          </Button>
        ))}
      </div>
      <EditFormWrapper 
        title={`编辑人物: ${selectedId}`} 
        description="修改人物核心设定，注意高风险字段会触发二次确认"
        reason={reason} setReason={setReason}
        confirmHighRisk={confirmHighRisk} setConfirmHighRisk={setConfirmHighRisk}
        onSave={handleSave} isHighRisk={true}
      >
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>真实姓名 (High Risk)</Label>
            <Input value={formData.true_name} onChange={e => setFormData({...formData, true_name: e.target.value})} />
          </div>
          <div className="space-y-2">
            <Label>当前状态 / 生死</Label>
            <Input value={formData.current_status} onChange={e => setFormData({...formData, current_status: e.target.value})} />
          </div>
          <div className="space-y-2 col-span-2 flex items-center gap-2 mt-4">
            <Switch checked={formData.true_name_revealed_to_reader} onCheckedChange={c => setFormData({...formData, true_name_revealed_to_reader: c})} />
            <Label className="text-red-400">是否已向读者揭露真实姓名 (High Risk)</Label>
          </div>
          <div className="space-y-2 col-span-2">
            <Label>哪些角色知道真实姓名 (逗号分隔)</Label>
            <Input value={formData.true_name_revealed_to_characters} onChange={e => setFormData({...formData, true_name_revealed_to_characters: e.target.value})} placeholder="例如: 女主, 皇帝" />
          </div>
        </div>
      </EditFormWrapper>
    </div>
  )
}

export function NameRulesEditTab({ stateData, loadData }: any) {
  const { projectId } = useProjectContext()
  const rules = stateData?.name_usage_rules?.rules || []
  const chars = stateData?.character_state?.characters || []
  
  const [selectedId, setSelectedId] = useState(chars[0]?.id || "")
  const [formData, setFormData] = useState<any>({})
  const [reason, setReason] = useState("")
  const [confirmHighRisk, setConfirmHighRisk] = useState(false)
  
  useEffect(() => {
    const r = rules.find((x: any) => x.character_id === selectedId) || {}
    setFormData({
      current_default_narration_name: r.current_default_narration_name || "",
      public_dialogue: r.public_dialogue || "",
      private_dialogue: r.private_dialogue || "",
    })
  }, [selectedId, rules])

  const handleSave = async () => {
    if (!reason.trim()) return toast.error("请输入修改原因")
    try {
      await api.client.patch(`/api/v1/projects/${projectId}/state/name-rules/${selectedId}`, {
        updates: formData, reason, confirm_high_risk: confirmHighRisk
      })
      toast.success("称呼规则更新成功")
      setReason(""); setConfirmHighRisk(false)
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || "更新失败")
    }
  }

  return (
    <div className="flex h-full gap-4 pt-2">
      <div className="w-48 flex flex-col gap-2 overflow-y-auto border-r pr-2">
        {chars.map((ch: any) => (
          <Button 
            key={ch.id} 
            variant={selectedId === ch.id ? "default" : "ghost"} 
            className="justify-start"
            onClick={() => setSelectedId(ch.id)}
          >
            {ch.display_name || ch.id}
          </Button>
        ))}
      </div>
      <EditFormWrapper 
        title={`编辑称呼规则: ${selectedId}`} 
        description="严格约束旁白与其他角色的称呼，防止 AI 幻觉泄露真名"
        reason={reason} setReason={setReason}
        confirmHighRisk={confirmHighRisk} setConfirmHighRisk={setConfirmHighRisk}
        onSave={handleSave} isHighRisk={true}
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>当前旁白默认称呼 (High Risk)</Label>
            <Input value={formData.current_default_narration_name} onChange={e => setFormData({...formData, current_default_narration_name: e.target.value})} placeholder="例如: 十四叔" />
            <p className="text-xs text-muted-foreground">如果真名未揭露，旁白不能使用真名</p>
          </div>
          <div className="space-y-2">
            <Label>公开场合称呼 (Public Dialogue)</Label>
            <Input value={formData.public_dialogue} onChange={e => setFormData({...formData, public_dialogue: e.target.value})} />
          </div>
          <div className="space-y-2">
            <Label>私下对话称呼 (Private Dialogue)</Label>
            <Input value={formData.private_dialogue} onChange={e => setFormData({...formData, private_dialogue: e.target.value})} placeholder="例如: 女主私下可称呼林惊羽" />
          </div>
        </div>
      </EditFormWrapper>
    </div>
  )
}

export function PlotThreadsEditTab({ stateData, loadData }: any) {
  const { projectId } = useProjectContext()
  const threads = stateData?.plot_threads?.threads || []
  
  const [selectedId, setSelectedId] = useState(threads[0]?.id || "")
  const [formData, setFormData] = useState<any>({})
  const [reason, setReason] = useState("")
  const [confirmHighRisk, setConfirmHighRisk] = useState(false)
  
  useEffect(() => {
    const t = threads.find((x: any) => x.id === selectedId) || {}
    setFormData({
      status: t.status || "active",
      planned_resolution: t.planned_resolution || ""
    })
  }, [selectedId, threads])

  const handleSave = async () => {
    if (!reason.trim()) return toast.error("请输入修改原因")
    try {
      await api.client.patch(`/api/v1/projects/${projectId}/state/plot-threads/${selectedId}`, {
        updates: formData, reason, confirm_high_risk: confirmHighRisk
      })
      toast.success("伏笔更新成功")
      setReason(""); setConfirmHighRisk(false)
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || "更新失败")
    }
  }

  return (
    <div className="flex h-full gap-4 pt-2">
      <div className="w-48 flex flex-col gap-2 overflow-y-auto border-r pr-2">
        {threads.map((t: any) => (
          <Button 
            key={t.id} 
            variant={selectedId === t.id ? "default" : "ghost"} 
            className="justify-start truncate"
            onClick={() => setSelectedId(t.id)}
            title={t.title}
          >
            {t.title}
          </Button>
        ))}
      </div>
      <EditFormWrapper 
        title={`编辑伏笔: ${selectedId}`} 
        description="修改伏笔/秘密的状态"
        reason={reason} setReason={setReason}
        confirmHighRisk={confirmHighRisk} setConfirmHighRisk={setConfirmHighRisk}
        onSave={handleSave} isHighRisk={true}
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>状态 (status)</Label>
            <select 
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
              value={formData.status} 
              onChange={e => setFormData({...formData, status: e.target.value})}
            >
              <option value="active">Active (活跃)</option>
              <option value="deepened">Deepened (加深)</option>
              <option value="partially_revealed">Partially Revealed (部分揭露)</option>
              <option value="resolved">Resolved (已解决)</option>
              <option value="abandoned">Abandoned (废弃)</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label>计划结局 (Planned Resolution)</Label>
            <Textarea 
              value={formData.planned_resolution} 
              onChange={e => setFormData({...formData, planned_resolution: e.target.value})} 
              rows={4}
            />
          </div>
        </div>
      </EditFormWrapper>
    </div>
  )
}

export function GlobalSummaryEditTab({ stateData, loadData }: any) {
  const { projectId } = useProjectContext()
  const summary = stateData?.global_summary || ""
  
  const [formData, setFormData] = useState<any>({ text: summary })
  const [reason, setReason] = useState("")
  const [confirmHighRisk, setConfirmHighRisk] = useState(false)
  
  useEffect(() => {
    setFormData({ text: stateData?.global_summary || "" })
  }, [stateData?.global_summary])

  const handleSave = async () => {
    if (!reason.trim()) return toast.error("请输入修改原因")
    try {
      await api.client.patch(`/api/v1/projects/${projectId}/state/summary`, {
        updates: formData, reason, confirm_high_risk: confirmHighRisk
      })
      toast.success("全局摘要更新成功")
      setReason(""); setConfirmHighRisk(false)
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || "更新失败")
    }
  }

  return (
    <div className="flex h-full pt-2">
      <EditFormWrapper 
        title="编辑全局摘要 (Global Summary)" 
        description="手动修正AI提炼错误的事实、死亡状态或秘密揭露结论。全局摘要修改永远被视为高风险操作。"
        reason={reason} setReason={setReason}
        confirmHighRisk={confirmHighRisk} setConfirmHighRisk={setConfirmHighRisk}
        onSave={handleSave} isHighRisk={true}
      >
        <div className="space-y-2 h-[400px] flex flex-col">
          <Label>正文摘要 Markdown</Label>
          <Textarea 
            className="flex-1 font-mono text-sm"
            value={formData.text} 
            onChange={e => setFormData({ text: e.target.value })} 
          />
        </div>
      </EditFormWrapper>
    </div>
  )
}
