"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Plus, Trash2, Edit3, Swords, Users } from "lucide-react"
import type { CharacterConflict, CharacterProfile } from "@/lib/types"
import { CONFLICT_TYPE_LABELS } from "@/lib/types"

interface Props {
  projectId: string
  characters: CharacterProfile[]
}

interface ConflictForm {
  title: string
  description: string
  conflict_type: string
  intensity: number
  start_chapter: number | null
  resolved_chapter: number | null
  resolution: string
  status: string
  participant_ids: number[]
}

const CONFLICT_STATUS_LABELS: Record<string, string> = {
  brewing: "酝酿中", active: "进行中", escalating: "升级中", climax: "高潮",
  subsiding: "缓和", resolved: "已解决",
}

export default function ConflictManager({ projectId, characters }: Props) {
  const [conflicts, setConflicts] = useState<CharacterConflict[]>([])
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CharacterConflict | null>(null)

  const [form, setForm] = useState<ConflictForm>({
    title: "", description: "", conflict_type: "", intensity: 0.5,
    start_chapter: null, resolved_chapter: null, resolution: "",
    status: "active", participant_ids: [],
  })

  const load = useCallback(async () => {
    setLoading(true)
    try { setConflicts(await api.characterConflicts.list(projectId)) }
    catch (e: any) { toast.error(e?.message || "加载冲突数据失败") }
    finally { setLoading(false) }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const resetForm = () => {
    setForm({ title: "", description: "", conflict_type: "", intensity: 0.5, start_chapter: null, resolved_chapter: null, resolution: "", status: "active", participant_ids: [] })
    setEditing(null)
  }

  const openCreate = () => { resetForm(); setDialogOpen(true) }
  const openEdit = (c: CharacterConflict) => {
    setEditing(c)
    setForm({
      title: c.title, description: c.description, conflict_type: c.conflict_type,
      intensity: c.intensity, start_chapter: c.start_chapter,
      resolved_chapter: c.resolved_chapter, resolution: c.resolution,
      status: c.status, participant_ids: c.participants.map(p => p.character_id),
    })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error("请输入冲突标题"); return }
    try {
      if (editing) { await api.characterConflicts.update(projectId, editing.id, form) }
      else { await api.characterConflicts.create(projectId, form) }
      toast.success(editing ? "冲突已更新" : "冲突已创建")
      setDialogOpen(false); load()
    } catch (e: any) { toast.error(e?.message || "保存失败") }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return
    try { await api.characterConflicts.delete(projectId, id); toast.success("已删除"); load() }
    catch (e: any) { toast.error(e?.message || "删除失败") }
  }

  const toggleParticipant = (charId: number) => setForm(f => ({
    ...f, participant_ids: f.participant_ids.includes(charId)
      ? f.participant_ids.filter(id => id !== charId) : [...f.participant_ids, charId],
  }))

  const update = (key: keyof ConflictForm, value: any) => setForm(f => ({ ...f, [key]: value } as ConflictForm))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div><h3 className="text-lg font-semibold">人物冲突网</h3><p className="text-sm text-muted-foreground">管理角色之间的冲突结构和演变轨迹</p></div>
        <Button onClick={openCreate} size="sm"><Plus className="h-4 w-4 mr-1" />新增冲突</Button>
      </div>
      {loading ? <div className="space-y-2"><Skeleton className="h-16 w-full" /></div>
      : conflicts.length === 0 ? <Card className="border-dashed"><CardContent className="py-8 text-center text-sm text-muted-foreground">暂无冲突记录</CardContent></Card>
      : <ScrollArea className="h-[400px]"><div className="space-y-2">
        {conflicts.map(c => (
          <Card key={c.id} className="hover:bg-accent/30"><CardContent className="p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Swords className="h-4 w-4 text-orange-500" /><span className="font-medium">{c.title}</span>
                  <Badge variant="outline">{CONFLICT_TYPE_LABELS[c.conflict_type] || c.conflict_type}</Badge>
                  <Badge variant={c.status === "active" || c.status === "escalating" ? "destructive" : "secondary"}>{CONFLICT_STATUS_LABELS[c.status] || c.status}</Badge>
                </div>
                {c.description && <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{c.description}</p>}
                <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                  <span>强度: {"★".repeat(Math.round(c.intensity * 5))}</span>
                  {c.participants?.length > 0 && <><span>|</span><span className="flex items-center gap-1"><Users className="h-3 w-3" />{c.participants.map(p => p.name).join(" · ")}</span></>}
                </div>
              </div>
              <div className="flex gap-1 shrink-0">
                <Button variant="ghost" size="icon" onClick={() => openEdit(c)}><Edit3 className="h-4 w-4" /></Button>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(c.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
              </div>
            </div>
          </CardContent></Card>
        ))}
      </div></ScrollArea>}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{editing ? "编辑冲突" : "新增冲突"}</DialogTitle><DialogDescription>记录角色之间的冲突结构</DialogDescription></DialogHeader>
          <div className="space-y-3">
            <div><Label>标题</Label><Input value={form.title} onChange={e => update("title", e.target.value)} placeholder="如：主角与反派的理念之争" /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>冲突类型</Label>
                <Select value={form.conflict_type} onValueChange={v => update("conflict_type", v)}>
                  <SelectTrigger><SelectValue placeholder="选择类型" /></SelectTrigger>
                  <SelectContent>{Object.entries(CONFLICT_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>状态</Label>
                <Select value={form.status} onValueChange={v => update("status", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(CONFLICT_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div><Label>描述</Label><Textarea rows={3} value={form.description} onChange={e => update("description", e.target.value)} placeholder="冲突背景和关键事件..." /></div>
            <div className="grid grid-cols-3 gap-2">
              <div><Label>强度 ({form.intensity.toFixed(1)})</Label><Input type="range" min="0" max="1" step="0.1" value={form.intensity} onChange={e => update("intensity", Number(e.target.value))} /></div>
              <div><Label>起始章节</Label><Input type="number" value={form.start_chapter ?? ""} onChange={e => update("start_chapter", e.target.value ? Number(e.target.value) : null)} /></div>
              <div><Label>解决章节</Label><Input type="number" value={form.resolved_chapter ?? ""} onChange={e => update("resolved_chapter", e.target.value ? Number(e.target.value) : null)} /></div>
            </div>
            <div><Label>参与方</Label>
              <div className="flex flex-wrap gap-1 mt-1">
                {characters.map(c => <Badge key={c.id} variant={form.participant_ids.includes(c.id) ? "default" : "outline"} className="cursor-pointer" onClick={() => toggleParticipant(c.id)}>{c.name}</Badge>)}
              </div>
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button><Button onClick={handleSave}>{editing ? "保存" : "创建"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
