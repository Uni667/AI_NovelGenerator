"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Plus, Trash2, Edit3, Clock, Calendar, Loader2, Eye } from "lucide-react"
import type { CharacterAppearance, CharacterProfile, TimelineEntry } from "@/lib/types"
import { APPEARANCE_TYPE_LABELS } from "@/lib/types"

interface Props {
  projectId: string
  characters: CharacterProfile[]
}

const ROLE_LABELS: Record<string, string> = {
  pov: "主视角", major: "主要配角", minor: "次要配角", background: "背景",
}

export default function AppearanceTimeline({ projectId, characters }: Props) {
  const [appearances, setAppearances] = useState<CharacterAppearance[]>([])
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState<"list" | "timeline">("timeline")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CharacterAppearance | null>(null)

  const [form, setForm] = useState({
    character_id: 0,
    chapter_number: 1,
    appearance_type: "present",
    role_in_chapter: "major",
    summary: "",
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [apps, tl] = await Promise.all([
        api.characterAppearances.list(projectId),
        api.characterAppearances.timeline(projectId).catch(() => []),
      ])
      setAppearances(apps)
      setTimeline(tl)
    } catch (e: any) {
      toast.error(e?.message || "加载登场数据失败")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const resetForm = () => {
    setForm({ character_id: 0, chapter_number: 1, appearance_type: "present", role_in_chapter: "major", summary: "" })
    setEditing(null)
  }

  const openCreate = () => { resetForm(); setDialogOpen(true) }
  const openEdit = (a: CharacterAppearance) => {
    setEditing(a)
    setForm({
      character_id: a.character_id,
      chapter_number: a.chapter_number,
      appearance_type: a.appearance_type,
      role_in_chapter: a.role_in_chapter,
      summary: a.summary,
    })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.character_id || !form.chapter_number) { toast.error("请选择角色和章节"); return }
    try {
      if (editing) {
        await api.characterAppearances.update(projectId, editing.id, form)
      } else {
        await api.characterAppearances.create(projectId, form)
      }
      toast.success(editing ? "记录已更新" : "记录已创建")
      setDialogOpen(false)
      load()
    } catch (e: any) {
      toast.error(e?.message || "保存失败")
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return
    try {
      await api.characterAppearances.delete(projectId, id)
      toast.success("已删除")
      load()
    } catch (e: any) {
      toast.error(e?.message || "删除失败")
    }
  }

  const charName = (id: number) => characters.find(c => c.id === id)?.name || `#${id}`

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">角色登场时间线</h3>
          <p className="text-sm text-muted-foreground">追踪角色在各章节的登场/退场/转变</p>
        </div>
        <Button onClick={openCreate} size="sm"><Plus className="h-4 w-4 mr-1" />新增登场记录</Button>
      </div>

      <Tabs value={viewMode} onValueChange={v => setViewMode(v as "list" | "timeline")}>
        <TabsList className="mb-2">
          <TabsTrigger value="timeline"><Calendar className="h-4 w-4 mr-1" />时间线视图</TabsTrigger>
          <TabsTrigger value="list"><Eye className="h-4 w-4 mr-1" />列表视图</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline">
          {loading ? (
            <div className="space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
          ) : timeline.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                暂无登场记录，点击"新增登场记录"开始构建时间线
              </CardContent>
            </Card>
          ) : (
            <ScrollArea className="h-[500px]">
              <div className="relative pl-6 border-l-2 border-muted space-y-3">
                {timeline.map(entry => (
                  <div key={entry.chapter_number} className="relative">
                    <div className="absolute -left-[25px] top-1 w-4 h-4 rounded-full bg-primary border-2 border-background" />
                    <Card className="hover:bg-accent/20 transition-colors">
                      <CardContent className="p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="default">第 {entry.chapter_number} 章</Badge>
                          <span className="text-xs text-muted-foreground">{entry.character_count} 个角色</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {entry.entries.map(e => (
                            <Badge key={e.id} variant="outline" className="text-xs cursor-help" title={`${APPEARANCE_TYPE_LABELS[e.appearance_type] || e.appearance_type} · ${ROLE_LABELS[e.role_in_chapter] || e.role_in_chapter}`}>
                              {e.character_name}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </TabsContent>

        <TabsContent value="list">
          {loading ? (
            <div className="space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
          ) : appearances.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                暂无登场记录
              </CardContent>
            </Card>
          ) : (
            <ScrollArea className="h-[400px]">
              <div className="space-y-1">
                {appearances.map(a => (
                  <Card key={a.id} className="hover:bg-accent/30 transition-colors">
                    <CardContent className="p-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium text-sm">{a.character_name}</span>
                          <Badge variant="secondary" className="text-xs">{APPEARANCE_TYPE_LABELS[a.appearance_type] || a.appearance_type}</Badge>
                          <Badge variant="outline" className="text-xs">第{a.chapter_number}章</Badge>
                          <span className="text-xs text-muted-foreground">{ROLE_LABELS[a.role_in_chapter] || a.role_in_chapter}</span>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(a)}><Edit3 className="h-3 w-3" /></Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDelete(a.id)}><Trash2 className="h-3 w-3 text-destructive" /></Button>
                        </div>
                      </div>
                      {a.summary && <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{a.summary}</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? "编辑登场记录" : "新增登场记录"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>角色</Label>
              <Select value={String(form.character_id)} onValueChange={v => setForm(f => ({ ...f, character_id: Number(v) }))}>
                <SelectTrigger><SelectValue placeholder="选择角色" /></SelectTrigger>
                <SelectContent>
                  {characters.map(c => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>章节号</Label>
                <Input type="number" min={1} value={form.chapter_number} onChange={e => setForm(f => ({ ...f, chapter_number: Number(e.target.value) }))} />
              </div>
              <div>
                <Label>登场类型</Label>
                <Select value={form.appearance_type} onValueChange={v => setForm(f => ({ ...f, appearance_type: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(APPEARANCE_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>角色定位</Label>
              <Select value={form.role_in_chapter} onValueChange={v => setForm(f => ({ ...f, role_in_chapter: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(ROLE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>简述</Label>
              <Textarea rows={2} value={form.summary} onChange={e => setForm(f => ({ ...f, summary: e.target.value }))} placeholder="角色在本章的行动概要..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSave}>{editing ? "保存" : "创建"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
