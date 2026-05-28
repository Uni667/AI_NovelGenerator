"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Users, UserPlus, Upload, Sparkles, Trash2, PlusCircle, GitBranch, Swords, Clock, Loader2 } from "lucide-react"
import { api } from "@/lib/api-client"
import RelationshipManager from "@/components/character/RelationshipManager"
import ConflictManager from "@/components/character/ConflictManager"
import AppearanceTimeline from "@/components/character/AppearanceTimeline"

interface CharactersTabProps {
  id: string
}

const CHARACTER_STATUS_OPTIONS = [
  { value: "appeared", label: "已出现" },
  { value: "planned", label: "计划登场" },
  { value: "suggested", label: "AI 建议" },
] as const

const CHARACTER_SOURCE_OPTIONS = [
  { value: "user", label: "我设定" },
  { value: "ai", label: "AI 生成" },
] as const

const characterStatusLabel = (status?: string) => {
  return CHARACTER_STATUS_OPTIONS.find((item) => item.value === status)?.label || "已出现"
}

const characterSourceLabel = (source?: string) => {
  return CHARACTER_SOURCE_OPTIONS.find((item) => item.value === source)?.label || "我设定"
}

export function CharactersTab({ id }: CharactersTabProps) {
  const [characters, setCharacters] = useState<any[]>([])
  const [dashboardSummary, setDashboardSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [charDialogOpen, setCharDialogOpen] = useState(false)
  const [editChar, setEditChar] = useState<any>(null)
  const [charName, setCharName] = useState("")
  const [charDesc, setCharDesc] = useState("")
  const [charStatus, setCharStatus] = useState<"appeared" | "planned" | "suggested">("planned")
  const [charSource, setCharSource] = useState<"user" | "ai">("user")
  const [charFirstChapter, setCharFirstChapter] = useState<number | "">("")
  const [deleteCharTarget, setDeleteCharTarget] = useState<number | null>(null)
  const [characterSuggestions, setCharacterSuggestions] = useState<any[]>([])
  const [characterLoading, setCharacterLoading] = useState("")
  const [planOutline, setPlanOutline] = useState("")

  const [characterImportPreviewOpen, setCharacterImportPreviewOpen] = useState(false)
  const [characterImportCandidates, setCharacterImportCandidates] = useState<any[]>([])
  const [characterImportSummary, setCharacterImportSummary] = useState<any>({})
  const [characterImportSelectedIds, setCharacterImportSelectedIds] = useState<string[]>([])
  const [characterImportLoading, setCharacterImportLoading] = useState(false)
  const [characterImportConfirming, setCharacterImportConfirming] = useState(false)

  const loadCharacters = useCallback(async () => {
    try {
      const data = await api.characters.list(id)
      setCharacters(data)
    } catch {
      toast.error("加载角色列表失败")
    }
  }, [id])

  const loadDashboard = useCallback(async () => {
    try {
      const { summary } = await api.characters.dashboard(id)
      setDashboardSummary(summary)
    } catch {
      // Ignore dashboard load failures silently
    }
  }, [id])

  const initData = useCallback(async () => {
    setLoading(true)
    await Promise.all([loadCharacters(), loadDashboard()])
    setLoading(false)
  }, [loadCharacters, loadDashboard])

  useEffect(() => {
    initData()
  }, [initData])

  const handleCreateCharacter = async () => {
    if (!charName.trim()) return
    try {
      await api.characters.create(id, {
        name: charName,
        description: charDesc,
        status: charStatus,
        source: charSource,
        first_appearance_chapter: charFirstChapter === "" ? null : Number(charFirstChapter),
      })
      toast.success("角色已创建")
      setCharDialogOpen(false)
      setCharName("")
      setCharDesc("")
      setCharFirstChapter("")
      await initData()
    } catch (e: any) {
      toast.error(e?.message || "创建角色失败")
    }
  }

  const handleUpdateCharacter = async () => {
    if (!editChar || !charName.trim()) return
    try {
      await api.characters.update(id, editChar.id, {
        name: charName,
        description: charDesc,
        status: charStatus,
        source: charSource,
        first_appearance_chapter: charFirstChapter === "" ? null : Number(charFirstChapter),
      })
      toast.success("角色已更新")
      setEditChar(null)
      setCharDialogOpen(false)
      setCharFirstChapter("")
      await initData()
    } catch (e: any) {
      toast.error(e?.message || "更新角色失败")
    }
  }

  const handleDeleteCharacter = async () => {
    if (deleteCharTarget === null) return
    try {
      await api.characters.delete(id, deleteCharTarget)
      toast.success("角色已删除")
      setDeleteCharTarget(null)
      await initData()
    } catch (e: any) {
      toast.error(e?.message || "删除角色失败")
    }
  }

  const handleImportCharacters = async () => {
    setCharacterImportLoading(true)
    try {
      const result = await api.characters.importPreview(id)
      const candidates = result.candidates || []
      setCharacterImportSummary(result.summary || {})
      setCharacterImportCandidates(candidates)
      setCharacterImportSelectedIds(
        candidates
          .filter((candidate: any) => candidate.decision !== "reject")
          .map((candidate: any) => candidate.candidate_id)
      )
      setCharacterImportPreviewOpen(true)
    } catch (error: any) {
      toast.error(error?.message || "角色导入预览失败")
    } finally {
      setCharacterImportLoading(false)
    }
  }

  const handleConfirmCharacterImport = async () => {
    if (characterImportSelectedIds.length === 0) {
      toast.error("请至少选择一个候选角色")
      return
    }
    setCharacterImportConfirming(true)
    try {
      const result = await api.characters.importFromState(id, {
        selected_candidate_ids: characterImportSelectedIds,
      })
      toast.success(`成功导入 ${result.length} 个角色`)
      setCharacterImportPreviewOpen(false)
      setCharacterImportCandidates([])
      setCharacterImportSelectedIds([])
      setCharacterImportSummary({})
      await initData()
    } catch (error: any) {
      toast.error(error?.message || "角色导入失败")
    } finally {
      setCharacterImportConfirming(false)
    }
  }

  const selectCharacterImportCandidates = (mode: "recommended" | "all" | "none") => {
    if (mode === "none") {
      setCharacterImportSelectedIds([])
      return
    }
    if (mode === "all") {
      setCharacterImportSelectedIds(characterImportCandidates.map((candidate: any) => candidate.candidate_id))
      return
    }
    setCharacterImportSelectedIds(
      characterImportCandidates
        .filter((candidate: any) => candidate.decision !== "reject")
        .map((candidate: any) => candidate.candidate_id)
    )
  }

  const toggleCharacterImportCandidate = (candidateId: string) => {
    setCharacterImportSelectedIds((current) =>
      current.includes(candidateId)
        ? current.filter((item) => item !== candidateId)
        : [...current, candidateId]
    )
  }

  const handleSuggestCharacters = async () => {
    setCharacterLoading("suggest")
    try {
      const result = await api.characters.suggest(id)
      setCharacterSuggestions(result.characters || [])
      setPlanOutline("")
      toast.success(`已生成 ${result.characters?.length || 0} 个角色建议`)
    } catch (error: any) {
      toast.error(error?.message || "角色建议生成失败")
    } finally {
      setCharacterLoading("")
    }
  }

  const handlePlanCharacters = async () => {
    setCharacterLoading("plan")
    setPlanOutline("")
    try {
      const result = await api.characters.plan(id)
      setCharacterSuggestions(result.characters || [])
      if (result.outline) {
        setPlanOutline(result.outline)
      }
      toast.success(`已生成 ${result.characters?.length || 0} 个规划角色及剧情大纲`)
    } catch (error: any) {
      toast.error(error?.message || "人物规划生成失败")
    } finally {
      setCharacterLoading("")
    }
  }

  const handleAcceptCharacterSuggestion = async (suggestion: any) => {
    try {
      await api.characters.create(id, {
        name: suggestion.name,
        description: suggestion.description,
        status: "planned",
        source: "ai",
        first_appearance_chapter: suggestion.first_appearance_chapter ?? null,
      })
      toast.success("已加入计划登场")
      setCharacterSuggestions((items) => items.filter((item) => item.name !== suggestion.name))
      await initData()
    } catch (e: any) {
      toast.error(e?.message || "采纳建议失败")
    }
  }

  const openEditDialog = (char: any) => {
    setEditChar(char)
    setCharName(char.name)
    setCharDesc(char.description || "")
    setCharStatus(char.status || "appeared")
    setCharSource(char.source || "user")
    setCharFirstChapter(char.first_appearance_chapter ?? "")
    setCharDialogOpen(true)
  }

  const openCreateDialog = (status = "planned", source = "user") => {
    setEditChar(null)
    setCharName("")
    setCharDesc("")
    setCharStatus(status as any)
    setCharSource(source as any)
    setCharFirstChapter("")
    setCharDialogOpen(true)
  }

  const appearedCharacters = characters.filter((char: any) => (char.status || "appeared") === "appeared")
  const plannedCharacters = characters.filter((char: any) => char.status === "planned")
  const suggestedCharacters = characters.filter((char: any) => char.status === "suggested")

  if (loading && characters.length === 0) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-64 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 shadow-xl">
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-xl font-bold tracking-tight">
                <Users className="h-5 w-5 text-primary animate-pulse" />
                人物规划
              </CardTitle>
              <CardDescription>管理小说角色资料、情感关系网、主线冲突及登场时间线</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleImportCharacters}
                disabled={characterImportLoading}
                className="hover:bg-accent/40"
              >
                {characterImportLoading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2 text-indigo-400" />
                )}
                预览导入
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSuggestCharacters}
                disabled={characterLoading === "suggest"}
                className="hover:bg-accent/40"
              >
                {characterLoading === "suggest" ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2 text-purple-400" />
                )}
                AI 建议人物
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handlePlanCharacters}
                disabled={characterLoading === "plan"}
                className="hover:bg-accent/40 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border-indigo-500/30 transition-transform duration-200 hover:scale-105"
              >
                {characterLoading === "plan" ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2 text-indigo-400" />
                )}
                规划人物大纲
              </Button>
              <Button
                size="sm"
                onClick={() => openCreateDialog("planned", "user")}
                className="shadow-md shadow-primary/20 hover:scale-102 transition-transform duration-200"
              >
                <UserPlus className="h-4 w-4 mr-2" />
                新增计划人物
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* 角色库概览 */}
      {dashboardSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              label: "总人物",
              value: dashboardSummary.total_characters,
              sub: `${dashboardSummary.appeared}登场 · ${dashboardSummary.planned}计划 · ${dashboardSummary.suggested}建议`,
            },
            {
              label: "总关系",
              value: dashboardSummary.total_relationships,
              sub: `${dashboardSummary.active_relationships} 活跃`,
            },
            {
              label: "冲突事件",
              value: dashboardSummary.total_conflicts,
              sub: `${dashboardSummary.active_conflicts} 进行中`,
            },
            {
              label: "登场章节",
              value: dashboardSummary.total_appearances,
              sub: `${dashboardSummary.chapters_with_data} 章有数据`,
            },
          ].map((s) => (
            <Card key={s.label} className="glass-card border-border/40 hover:border-primary/20 transition-all duration-300">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-extrabold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                  {s.value}
                </p>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mt-1">{s.label}</p>
                {s.sub && <p className="text-[11px] text-muted-foreground/80 mt-1">{s.sub}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 角色管理子标签 */}
      <Tabs defaultValue="roster" className="space-y-4">
        <TabsList className="bg-background/40 backdrop-blur-md border border-border/40 p-1 flex flex-nowrap overflow-x-auto max-w-full scrollbar-none h-auto">
          <TabsTrigger value="roster" className="data-[state=active]:bg-primary/25 shrink-0">
            <Users className="h-4 w-4 mr-1.5" />人物列表
          </TabsTrigger>
          <TabsTrigger value="relationships" className="data-[state=active]:bg-primary/25 shrink-0">
            <GitBranch className="h-4 w-4 mr-1.5" />关系图
          </TabsTrigger>
          <TabsTrigger value="conflicts" className="data-[state=active]:bg-primary/25 shrink-0">
            <Swords className="h-4 w-4 mr-1.5" />冲突网
          </TabsTrigger>
          <TabsTrigger value="timeline" className="data-[state=active]:bg-primary/25 shrink-0">
            <Clock className="h-4 w-4 mr-1.5" />登场时间线
          </TabsTrigger>
        </TabsList>

        <TabsContent value="roster" className="space-y-4">
          {planOutline && (
            <Card className="glass-panel border-border/40 border-l-indigo-500/50 border-l-4">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-indigo-400" />
                  本次规划大纲剧情建议
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <pre className="text-xs text-muted-foreground leading-relaxed font-sans whitespace-pre-wrap bg-muted/10 p-3 rounded-lg border border-border/20">
                  {planOutline}
                </pre>
                <div className="flex justify-end">
                  <Button size="sm" variant="outline" onClick={() => {
                    navigator.clipboard.writeText(planOutline);
                    toast.success("已复制到剪贴板");
                  }} className="h-7 text-xs border-indigo-500/25 hover:bg-indigo-500/10">
                    复制大纲
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {characterSuggestions.length > 0 && (
            <Card className="glass-panel border-border/40 border-l-purple-500/50 border-l-4">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-purple-400" />
                  本次 AI 建议人物
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {characterSuggestions.map((suggestion: any) => (
                  <div key={suggestion.name} className="rounded-xl border border-border/40 bg-card/25 p-4 hover:border-purple-500/30 transition-all">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-sm">{suggestion.name}</p>
                        <p className="mt-1 text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                          {suggestion.description}
                        </p>
                      </div>
                      <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/20 text-[10px] shrink-0">
                        AI 建议
                      </Badge>
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-2 border-t border-border/20 pt-3">
                      <span className="text-[11px] text-muted-foreground/80 font-medium">
                        {suggestion.first_appearance_chapter ? `预计第${suggestion.first_appearance_chapter}章` : "登场待定"}
                      </span>
                      <Button size="sm" variant="outline" onClick={() => handleAcceptCharacterSuggestion(suggestion)} className="h-7 text-xs border-purple-500/25 hover:bg-purple-500/10">
                        <PlusCircle className="h-3.5 w-3.5 mr-1" />采纳
                      </Button>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            {[
              {
                title: "已出现人物",
                items: appearedCharacters,
                badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                empty: "从角色状态导入后会出现在这里",
              },
              {
                title: "计划登场人物",
                items: plannedCharacters,
                badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
                empty: "你准备安排的后续人物会出现在这里",
              },
              {
                title: "AI 建议人物",
                items: suggestedCharacters,
                badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
                empty: "AI 生成但尚未采纳的人物会出现在这里",
              },
            ].map((group) => (
              <Card key={group.title} className="glass-panel border-border/40 flex flex-col">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-bold tracking-tight">{group.title}</CardTitle>
                    <Badge variant="secondary" className="font-mono text-xs">{group.items.length}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex-1">
                  {group.items.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-border/40 p-6 text-center text-xs text-muted-foreground/80 leading-relaxed bg-muted/5">
                      {group.empty}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {group.items.map((char: any) => (
                        <div
                          key={char.id}
                          className="rounded-xl border border-border/60 bg-card/10 p-3.5 hover:bg-accent/25 hover:border-primary/20 transition-all duration-200"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0 flex-1 cursor-pointer" onClick={() => openEditDialog(char)}>
                              <div className="flex flex-wrap items-center gap-1.5">
                                <p className="font-semibold text-sm hover:underline">{char.name}</p>
                                <Badge variant="outline" className={`text-[10px] scale-95 origin-left ${group.badgeColor}`}>
                                  {characterSourceLabel(char.source)}
                                </Badge>
                              </div>
                              {char.description && (
                                <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground leading-relaxed">
                                  {char.description}
                                </p>
                              )}
                              <p className="mt-2.5 text-[11px] text-muted-foreground/80 font-medium flex items-center gap-2">
                                <span>{characterStatusLabel(char.status)}</span>
                                {char.first_appearance_chapter && (
                                  <>
                                    <span className="text-muted-foreground/45">•</span>
                                    <span>第 {char.first_appearance_chapter} 章登场</span>
                                  </>
                                )}
                              </p>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setDeleteCharTarget(char.id)}
                              className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg shrink-0"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="relationships" className="glass-panel border border-border/40 p-6 rounded-xl">
          <RelationshipManager projectId={id} characters={characters} />
        </TabsContent>

        <TabsContent value="conflicts" className="glass-panel border border-border/40 p-6 rounded-xl">
          <ConflictManager projectId={id} characters={characters} />
        </TabsContent>

        <TabsContent value="timeline" className="glass-panel border border-border/40 p-6 rounded-xl">
          <AppearanceTimeline projectId={id} characters={characters} />
        </TabsContent>
      </Tabs>

      {/* 角色编辑对话框 */}
      <Dialog open={charDialogOpen} onOpenChange={(v) => { if (!v) { setCharDialogOpen(false); setEditChar(null) } }}>
        <DialogContent className="glass-panel border-border/40 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">{editChar ? "编辑角色" : "新增角色"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">角色名称</Label>
              <Input value={charName} onChange={e => setCharName(e.target.value)} placeholder="如：林逸" className="hover:border-primary/20" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">描述</Label>
              <Textarea value={charDesc} onChange={e => setCharDesc(e.target.value)} rows={4} placeholder="外貌特征、性格特点、核心动机或神秘身世..." className="hover:border-primary/20 resize-none leading-relaxed" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">人物状态</Label>
                <Select value={charStatus} onValueChange={(value) => value && setCharStatus(value)}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CHARACTER_STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">来源</Label>
                <Select value={charSource} onValueChange={(value) => value && setCharSource(value)}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CHARACTER_SOURCE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">预计 / 首次登场章节</Label>
              <Input
                type="number"
                min={1}
                value={charFirstChapter}
                onChange={(event) => setCharFirstChapter(event.target.value ? Math.max(1, Number(event.target.value) || 1) : "")}
                placeholder="留空表示待定"
                className="hover:border-primary/20"
              />
            </div>
            <Button className="w-full mt-2 shadow-md shadow-primary/25" onClick={editChar ? handleUpdateCharacter : handleCreateCharacter} disabled={!charName.trim()}>
              {editChar ? "保存修改" : "创建角色"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={deleteCharTarget !== null} onOpenChange={(v) => { if (!v) setDeleteCharTarget(null) }}>
        <DialogContent className="glass-panel border-border/40 max-w-sm text-center">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">确认删除此角色？</DialogTitle>
            <DialogDescription className="text-xs mt-1">
              删除角色将同步清空其相关的关系链和登场统计，此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex gap-2 justify-center sm:justify-center">
            <Button variant="outline" size="sm" onClick={() => setDeleteCharTarget(null)}>取消</Button>
            <Button variant="destructive" size="sm" onClick={handleDeleteCharacter}>确认删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 角色导入预览 */}
      <Dialog open={characterImportPreviewOpen} onOpenChange={(open) => { if (!open) setCharacterImportPreviewOpen(false) }}>
        <DialogContent className="glass-panel border-border/40 max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">导入角色候选列表</DialogTitle>
            <DialogDescription className="text-xs">
              AI 扫描小说文档后识别出的实体候选。勾选你希望添加到项目角色库的人选。
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 my-3">
            {[
              { label: "全部候选", val: characterImportSummary?.total ?? characterImportCandidates.length },
              { label: "推荐导入", val: characterImportSummary?.keep ?? 0 },
              { label: "待审阅", val: characterImportSummary?.review ?? 0 },
              { label: "当前选中", val: characterImportSelectedIds.length },
            ].map(c => (
              <div key={c.label} className="border border-border/30 rounded-xl p-3 bg-muted/10">
                <p className="text-[11px] text-muted-foreground font-medium">{c.label}</p>
                <p className="mt-1 text-xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">{c.val}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 mb-3">
            <Button variant="outline" size="sm" onClick={() => selectCharacterImportCandidates("recommended")} className="h-8 text-xs">选推荐项</Button>
            <Button variant="outline" size="sm" onClick={() => selectCharacterImportCandidates("all")} className="h-8 text-xs">全选</Button>
            <Button variant="ghost" size="sm" onClick={() => selectCharacterImportCandidates("none")} className="h-8 text-xs">清空</Button>
          </div>

          <ScrollArea className="h-[45vh] rounded-xl border border-border/40">
            <div className="space-y-3 p-4">
              {characterImportCandidates.length === 0 ? (
                <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                  没有找到新的角色候选项
                </div>
              ) : (
                characterImportCandidates.map((candidate: any) => {
                  const selected = characterImportSelectedIds.includes(candidate.candidate_id)
                  return (
                    <div
                      key={candidate.candidate_id}
                      className={`rounded-xl border border-border/40 p-4 transition-all duration-200 bg-card/5 hover:bg-accent/10 ${
                        selected ? "border-primary bg-primary/5" : ""
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 shrink-0 rounded border-border text-primary focus:ring-primary focus:ring-offset-background"
                          checked={selected}
                          onChange={() => toggleCharacterImportCandidate(candidate.candidate_id)}
                        />
                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <p className="font-semibold text-sm">{candidate.name}</p>
                            <Badge
                              variant="outline"
                              className={
                                candidate.decision === "keep"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px]"
                                  : candidate.decision === "review"
                                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]"
                                  : "bg-destructive/10 text-destructive border-destructive/20 text-[10px]"
                              }
                            >
                              {candidate.decision === "keep" ? "推荐" : candidate.decision === "review" ? "复核" : "建议排除"}
                            </Badge>
                            <Badge variant="outline" className="text-[10px] bg-secondary/80 text-muted-foreground">
                              {candidate.entity_type || "character"}
                            </Badge>
                            {candidate.existing_character_id && (
                              <Badge variant="secondary" className="text-[10px] bg-blue-500/15 text-blue-400">已存在</Badge>
                            )}
                          </div>
                          <p className="text-[11px] text-muted-foreground/80 font-medium">
                            置信度 {Math.round((candidate.confidence || 0) * 100)}% · 来源: {candidate.section || "未知分区"}
                            {candidate.first_appearance_chapter ? ` · 首次登场第 ${candidate.first_appearance_chapter} 章` : ""}
                          </p>
                          {candidate.description && (
                            <p className="text-xs text-muted-foreground leading-relaxed bg-muted/5 p-2 rounded-lg border border-border/20">
                              {candidate.description}
                            </p>
                          )}
                          {candidate.reasons?.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-1">
                              {candidate.reasons.slice(0, 4).map((reason: string, idx: number) => (
                                <Badge key={idx} variant="outline" className="text-[10px] scale-95 origin-left text-muted-foreground/90">{reason}</Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </ScrollArea>

          <DialogFooter className="mt-4">
            <Button variant="outline" size="sm" onClick={() => setCharacterImportPreviewOpen(false)}>取消</Button>
            <Button
              size="sm"
              onClick={handleConfirmCharacterImport}
              disabled={characterImportConfirming || characterImportSelectedIds.length === 0}
            >
              {characterImportConfirming ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              确认写入 ({characterImportSelectedIds.length} 个)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
