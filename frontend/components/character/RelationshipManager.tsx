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
import { Plus, Trash2, Edit3, GitBranch } from "lucide-react"
import type { CharacterRelationship, CharacterProfile, RelationshipGraph } from "@/lib/types"
import { RELATIONSHIP_TYPE_LABELS } from "@/lib/types"

interface Props {
  projectId: string
  characters: CharacterProfile[]
}

interface RelForm {
  character_id_a: number
  character_id_b: number
  rel_type: string
  description: string
  strength: number
  direction: string
  start_chapter: number | null
  status: string
}

const STATUS_LABELS: Record<string, string> = {
  active: "活跃", strained: "紧张", broken: "破裂", evolving: "演变中", resolved: "已化解",
}

export default function RelationshipManager({ projectId, characters }: Props) {
  const [relationships, setRelationships] = useState<CharacterRelationship[]>([])
  const [graph, setGraph] = useState<RelationshipGraph | null>(null)
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CharacterRelationship | null>(null)

  const [form, setForm] = useState<RelForm>({
    character_id_a: 0, character_id_b: 0, rel_type: "",
    description: "", strength: 0.5, direction: "bidirectional",
    start_chapter: null, status: "active",
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rels, g] = await Promise.all([
        api.characterRelationships.list(projectId),
        api.characterRelationships.graph(projectId).catch(() => null),
      ])
      setRelationships(rels)
      setGraph(g)
    } catch (e: any) {
      toast.error(e?.message || "加载关系数据失败")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const resetForm = () => {
    setForm({ character_id_a: 0, character_id_b: 0, rel_type: "", description: "", strength: 0.5, direction: "bidirectional", start_chapter: null, status: "active" })
    setEditing(null)
  }

  const openCreate = () => { resetForm(); setDialogOpen(true) }
  const openEdit = (rel: CharacterRelationship) => {
    setEditing(rel)
    setForm({
      character_id_a: rel.character_id_a, character_id_b: rel.character_id_b,
      rel_type: rel.rel_type, description: rel.description, strength: rel.strength,
      direction: rel.direction, start_chapter: rel.start_chapter, status: rel.status,
    })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.character_id_a || !form.character_id_b || form.character_id_a === form.character_id_b) {
      toast.error("请选择两个不同的角色"); return
    }
    try {
      if (editing) { await api.characterRelationships.update(projectId, editing.id, form) }
      else { await api.characterRelationships.create(projectId, form) }
      toast.success(editing ? "关系已更新" : "关系已创建")
      setDialogOpen(false); load()
    } catch (e: any) { toast.error(e?.message || "保存失败") }
  }

  const handleDelete = async (relId: number) => {
    if (!confirm("确定删除这条关系？")) return
    try { await api.characterRelationships.delete(projectId, relId); toast.success("已删除"); load() }
    catch (e: any) { toast.error(e?.message || "删除失败") }
  }

  const charName = (id: number) => characters.find(c => c.id === id)?.name || `#${id}`
  const update = (key: keyof RelForm, value: any) => setForm(f => ({ ...f, [key]: value } as RelForm))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div><h3 className="text-lg font-semibold">人物关系图</h3><p className="text-sm text-muted-foreground">管理角色之间的结构化关系</p></div>
        <Button onClick={openCreate} size="sm"><Plus className="h-4 w-4 mr-1" />新增关系</Button>
      </div>
      {loading ? <div className="space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
      : relationships.length === 0 ? <Card className="border-dashed"><CardContent className="py-8 text-center text-sm text-muted-foreground">暂无关系记录</CardContent></Card>
      : <>
        {graph && graph.nodes.length > 0 && (
          <Card className="bg-muted/20"><CardContent className="py-3">
            <div className="flex flex-wrap gap-1 items-center text-sm">
              <GitBranch className="h-4 w-4 mr-1 text-muted-foreground" />
              <span className="text-muted-foreground">{graph.nodes.length} 角色 · {graph.edges.length} 条关系</span>
            </div>
          </CardContent></Card>
        )}
        <ScrollArea className="h-[400px]"><div className="space-y-2">
          {relationships.map(rel => (
            <Card key={rel.id} className="hover:bg-accent/30"><CardContent className="p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium">{charName(rel.character_id_a)}</span>
                    <Badge variant="secondary" className="text-xs">{RELATIONSHIP_TYPE_LABELS[rel.rel_type] || rel.rel_type}</Badge>
                    <span className="text-muted-foreground">{rel.direction === "a_to_b" ? "→" : rel.direction === "b_to_a" ? "←" : "↔"}</span>
                    <span className="font-medium">{charName(rel.character_id_b)}</span>
                  </div>
                  {rel.description && <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{rel.description}</p>}
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span>强度: {"★".repeat(Math.round(rel.strength * 5))}</span>
                    <span>|</span><span>{STATUS_LABELS[rel.status] || rel.status}</span>
                    {rel.start_chapter && <><span>|</span><span>第{rel.start_chapter}章起</span></>}
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button variant="ghost" size="icon" onClick={() => openEdit(rel)}><Edit3 className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(rel.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                </div>
              </div>
            </CardContent></Card>
          ))}
        </div></ScrollArea>
      </>}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{editing ? "编辑关系" : "新增关系"}</DialogTitle><DialogDescription>定义两个角色之间的结构化关系</DialogDescription></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div><Label>角色 A</Label>
                <Select value={String(form.character_id_a)} onValueChange={v => update("character_id_a", Number(v))}>
                  <SelectTrigger><SelectValue placeholder="选择角色" /></SelectTrigger>
                  <SelectContent>{characters.map(c => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>角色 B</Label>
                <Select value={String(form.character_id_b)} onValueChange={v => update("character_id_b", Number(v))}>
                  <SelectTrigger><SelectValue placeholder="选择角色" /></SelectTrigger>
                  <SelectContent>{characters.map(c => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>关系类型</Label>
                <Select value={form.rel_type} onValueChange={v => update("rel_type", v)}>
                  <SelectTrigger><SelectValue placeholder="选择类型" /></SelectTrigger>
                  <SelectContent>{Object.entries(RELATIONSHIP_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>方向</Label>
                <Select value={form.direction} onValueChange={v => update("direction", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="bidirectional">双向</SelectItem><SelectItem value="a_to_b">A→B</SelectItem><SelectItem value="b_to_a">B→A</SelectItem></SelectContent>
                </Select>
              </div>
            </div>
            <div><Label>描述</Label><Textarea rows={3} value={form.description} onChange={e => update("description", e.target.value)} placeholder="关系描述..." /></div>
            <div className="grid grid-cols-3 gap-2">
              <div><Label>强度 ({form.strength.toFixed(1)})</Label><Input type="range" min="0" max="1" step="0.1" value={form.strength} onChange={e => update("strength", Number(e.target.value))} /></div>
              <div><Label>起始章节</Label><Input type="number" value={form.start_chapter ?? ""} onChange={e => update("start_chapter", e.target.value ? Number(e.target.value) : null)} placeholder="可选" /></div>
              <div><Label>状态</Label>
                <Select value={form.status} onValueChange={v => update("status", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button><Button onClick={handleSave}>{editing ? "保存" : "创建"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
