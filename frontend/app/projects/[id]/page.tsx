"use client"

import { useParams, useRouter } from "next/navigation"
import { useProject, useProjectConfig, useChapters, useUpdateProjectConfig } from "@/lib/hooks/use-projects"
import { useSSE } from "@/lib/hooks/use-sse"
import { api } from "@/lib/api-client"
import { PLATFORM_CONFIG, PLATFORMS } from "@/lib/types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useState, useEffect, useRef } from "react"
import { toast } from "sonner"
import { Play, FileText, BookOpen, Upload, Trash2, CheckCircle, AlertCircle, Loader2, Users, UserPlus, FileDown, Wand2, BookMarked, Target, Tag, FileEdit, RefreshCw } from "lucide-react"

export default function ProjectDashboard() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { data: project, isLoading } = useProject(id)
  const { data: config } = useProjectConfig(id)
  const { data: chapters } = useChapters(id)
  const updateConfig = useUpdateProjectConfig(id)
  const { events, isConnected, connect } = useSSE()
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const [activeTab, setActiveTab] = useState("overview")
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [characters, setCharacters] = useState<any[]>([])
  const [charDialogOpen, setCharDialogOpen] = useState(false)
  const [editChar, setEditChar] = useState<any>(null)
  const [charName, setCharName] = useState("")
  const [charDesc, setCharDesc] = useState("")
  const [deleteCharTarget, setDeleteCharTarget] = useState<number | null>(null)

  // 平台工具状态
  const [titles, setTitles] = useState<string[]>([])
  const [blurbs, setBlurbs] = useState<string[]>([])
  const [hookResult, setHookResult] = useState<any>(null)
  const [batchHookResult, setBatchHookResult] = useState<any[]>([])
  const [tagsResult, setTagsResult] = useState<any>(null)
  const [chapterTitles, setChapterTitles] = useState<string[]>([])
  const [platformLoading, setPlatformLoading] = useState("")
  const [hookChapterNum, setHookChapterNum] = useState(1)

  const lastProgress = events.filter(e => e.type === "progress").pop()
  const lastPartial = events.filter(e => e.type === "partial").pop()
  const hasError = events.some(e => e.type === "error")

  const debouncedUpdate = (data: Record<string, any>) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => updateConfig.mutate(data), 500)
  }

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [])

  const loadCharacters = async () => {
    try { setCharacters(await api.characters.list(id)) } catch { /* ignore */ }
  }

  useEffect(() => {
    if (activeTab === "characters") loadCharacters()
  }, [activeTab, id])

  const handleCreateCharacter = async () => {
    if (!charName.trim()) return
    await api.characters.create(id, { name: charName, description: charDesc })
    toast.success("角色已创建")
    setCharDialogOpen(false)
    setCharName("")
    setCharDesc("")
    loadCharacters()
  }

  const handleUpdateCharacter = async () => {
    if (!editChar || !charName.trim()) return
    await api.characters.update(id, editChar.id, { name: charName, description: charDesc })
    toast.success("角色已更新")
    setEditChar(null)
    setCharDialogOpen(false)
    loadCharacters()
  }

  const handleDeleteCharacter = async () => {
    if (deleteCharTarget === null) return
    await api.characters.delete(id, deleteCharTarget)
    toast.success("角色已删除")
    setDeleteCharTarget(null)
    loadCharacters()
  }

  const handleImportCharacters = async () => {
    const result = await api.characters.importFromState(id)
    toast.success(result.message || "导入完成")
    loadCharacters()
  }

  const openEditDialog = (char: any) => {
    setEditChar(char)
    setCharName(char.name)
    setCharDesc(char.description || "")
    setCharDialogOpen(true)
  }

  const openCreateDialog = () => {
    setEditChar(null)
    setCharName("")
    setCharDesc("")
    setCharDialogOpen(true)
  }

  const withLoading = async (key: string, fn: () => Promise<void>) => {
    setPlatformLoading(key)
    try { await fn() } catch (e: any) { toast.error(e.message || "操作失败") }
    finally { setPlatformLoading("") }
  }

  const handleGenTitles = () => withLoading("titles", async () => {
    const res = await api.platform.titles(id)
    setTitles(res.titles)
  })

  const handleGenBlurb = () => withLoading("blurb", async () => {
    const res = await api.platform.blurb(id)
    setBlurbs(res.blurbs)
  })

  const handleHookCheck = () => withLoading("hook", async () => {
    const res = await api.platform.hookCheck(id, hookChapterNum)
    setHookResult(res.analysis)
  })

  const handleBatchHookCheck = () => withLoading("batch", async () => {
    const res = await api.platform.batchHookCheck(id)
    setBatchHookResult(res.chapters || [])
  })

  const handleGenTags = () => withLoading("tags", async () => {
    const res = await api.platform.tags(id)
    setTagsResult(res.tags)
  })

  const handleGenChapterTitle = () => withLoading("chapterTitle", async () => {
    const res = await api.platform.chapterTitle(id, hookChapterNum)
    setChapterTitles(res.titles)
  })

  const handleGenerateArchitecture = () => {
    setActiveTab("generation")
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    connect(`${base}/api/v1/projects/${id}/generate/architecture?t=${Date.now()}`)
  }

  const handleGenerateBlueprint = () => {
    setActiveTab("generation")
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    connect(`${base}/api/v1/projects/${id}/generate/blueprint?t=${Date.now()}`)
  }

  const handleUploadKnowledge = async () => {
    if (!knowledgeFile) return
    const result = await api.knowledge.upload(id, knowledgeFile)
    toast.success(result.message || "上传成功")
    setKnowledgeFile(null)
  }

  const handleClearVector = async () => {
    await api.knowledge.clearVector(id)
    toast.success("向量库已清空")
    setClearDialogOpen(false)
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
        <Skeleton className="h-10 w-full max-w-md" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (!project) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="text-muted-foreground">{project.description || "暂无简介"}</p>
        </div>
        <Badge variant={project.status === "ready" ? "default" : "secondary"} className="text-sm px-3 py-1">
          {project.status === "draft" ? "草稿" : project.status === "ready" ? "就绪" : project.status}
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6 flex-wrap">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="generation">AI 生成</TabsTrigger>
          <TabsTrigger value="knowledge">知识库</TabsTrigger>
          <TabsTrigger value="characters">角色管理</TabsTrigger>
          <TabsTrigger value="platform">{PLATFORM_CONFIG[config?.platform]?.icon || "📖"} {PLATFORM_CONFIG[config?.platform]?.label || "平台"}工具</TabsTrigger>
          <TabsTrigger value="settings">参数设置</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">总章节</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{config?.num_chapters || 0}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">已完成</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{chapters?.filter((c: any) => c.status === "final").length || 0}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">目标平台</CardTitle></CardHeader>
              <CardContent>
                <span className="text-xl font-semibold">
                  {config?.platform ? <>{PLATFORM_CONFIG[config.platform]?.icon} {PLATFORM_CONFIG[config.platform]?.label}</> : "-"}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">分类</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.category || config?.genre || "-"}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">类型</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.genre || "-"}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">每章字数</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.word_number || "-"}</span></CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>快速操作</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button onClick={handleGenerateArchitecture} disabled={isConnected}>
                <Play className="h-4 w-4 mr-2" />生成架构
              </Button>
              <Button onClick={handleGenerateBlueprint} disabled={isConnected} variant="outline">
                <FileText className="h-4 w-4 mr-2" />生成章节目录
              </Button>
              <Separator orientation="vertical" className="h-8" />
              <Button variant="outline" onClick={() => api.export.download(id, "txt")}>
                <FileDown className="h-4 w-4 mr-2" />导出 TXT
              </Button>
              <Button variant="outline" onClick={() => api.export.download(id, "html")}>
                <FileDown className="h-4 w-4 mr-2" />导出 HTML
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>章节列表</CardTitle></CardHeader>
            <CardContent>
              {!chapters?.length ? (
                <p className="text-muted-foreground text-sm">尚未生成章节目录，请先执行「生成架构」→「生成章节目录」</p>
              ) : (
                <ScrollArea className="h-64">
                  <div className="space-y-2">
                    {chapters.map((ch: any) => (
                      <div
                        key={ch.chapter_number}
                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer"
                        onClick={() => router.push(`/projects/${id}/chapter/${ch.chapter_number}`)}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="font-mono text-sm text-muted-foreground shrink-0">第{ch.chapter_number}章</span>
                          <span className="font-medium truncate">{ch.chapter_title || "未命名"}</span>
                          {ch.chapter_summary && (
                            <span className="text-sm text-muted-foreground truncate hidden md:block max-w-xs">{ch.chapter_summary}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-2">
                          {ch.word_count > 0 && <span className="text-xs text-muted-foreground hidden sm:inline">{ch.word_count}字</span>}
                          <Badge variant={ch.status === "final" ? "default" : "secondary"}>
                            {ch.status === "final" ? "已定稿" : ch.status === "draft" ? "草稿" : "待生成"}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="generation">
          <Card>
            <CardHeader>
              <CardTitle>AI 生成进度</CardTitle>
              <CardDescription>实时显示生成状态</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {events.length === 0 && !isConnected && (
                <div className="text-center py-8 text-muted-foreground">
                  <Play className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>点击上方的「生成架构」或「生成章节目录」开始</p>
                </div>
              )}

              {isConnected && (
                <div className="flex items-center gap-2 text-primary">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>AI 正在生成中...</span>
                </div>
              )}

              {events.filter(e => e.type === "progress").map((e, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  {e.data.status === "done" ? (
                    <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
                  ) : (
                    <Loader2 className="h-5 w-5 animate-spin text-primary mt-0.5 shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="font-medium">{e.data.message}</p>
                    <p className="text-xs text-muted-foreground">步骤: {e.data.step}</p>
                  </div>
                </div>
              ))}

              {hasError && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-destructive/10 text-destructive">
                  <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
                  <p>生成过程中出现错误，请查看日志</p>
                </div>
              )}

              {lastPartial && (
                <div className="p-4 rounded-lg border bg-muted/30">
                  <p className="text-xs text-muted-foreground mb-2">生成预览：</p>
                  <pre className="text-sm whitespace-pre-wrap font-sans">{lastPartial.data.content}</pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="knowledge">
          <Card>
            <CardHeader>
              <CardTitle>知识库管理</CardTitle>
              <CardDescription>上传 TXT 设定文档，AI 会在生成章节时自动检索相关内容。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <Input type="file" accept=".txt,.md" onChange={e => setKnowledgeFile(e.target.files?.[0] || null)} className="flex-1" />
                <Button onClick={handleUploadKnowledge} disabled={!knowledgeFile}>
                  <Upload className="h-4 w-4 mr-2" />上传并导入
                </Button>
              </div>
              <Separator />
              <Button variant="destructive" onClick={() => setClearDialogOpen(true)}>
                <Trash2 className="h-4 w-4 mr-2" />清空向量库
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="characters">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <CardTitle>角色管理</CardTitle>
                  <CardDescription>管理小说中的角色信息</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleImportCharacters}>
                    <Upload className="h-4 w-4 mr-2" />从角色状态导入
                  </Button>
                  <Button size="sm" onClick={openCreateDialog}>
                    <UserPlus className="h-4 w-4 mr-2" />新增角色
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {characters.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>暂无角色，先生成架构后可从角色状态导入，或手动创建</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {characters.map((char: any) => (
                    <div key={char.id} className="flex items-start justify-between p-3 rounded-lg border hover:bg-accent">
                      <div className="flex-1 min-w-0 cursor-pointer" onClick={() => openEditDialog(char)}>
                        <p className="font-medium">{char.name}</p>
                        {char.description && <p className="text-sm text-muted-foreground truncate mt-1">{char.description}</p>}
                        <p className="text-xs text-muted-foreground mt-1">{new Date(char.updated_at).toLocaleDateString("zh-CN")}</p>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => setDeleteCharTarget(char.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 番茄平台工具 Tab */}
        <TabsContent value="platform">
          <div className="grid gap-6">
            {/* 1. 书名生成 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><BookMarked className="h-5 w-5" />AI 书名生成</CardTitle>
                <CardDescription>根据小说设定，用平台爆款公式（身份反转+冲突 / 悬念+关键词 / 情绪+结果前置）生成书名候选</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={handleGenTitles} disabled={platformLoading === "titles"}>
                  {platformLoading === "titles" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                  生成书名
                </Button>
                {titles.length > 0 && (
                  <div className="space-y-2">
                    {titles.map((t, i) => (
                      <div key={i} className="p-3 rounded-lg border bg-muted/30 text-sm flex items-start gap-2">
                        <Badge variant="outline" className="shrink-0 mt-0.5">{i + 1}</Badge>
                        <span>{t}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 2. 简介生成 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><FileEdit className="h-5 w-5" />AI 简介生成</CardTitle>
                <CardDescription>用「核心冲突 + 金手指 + 爽点预告 + 悬念钩子」公式生成平台式简介</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={handleGenBlurb} disabled={platformLoading === "blurb"}>
                  {platformLoading === "blurb" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                  生成简介
                </Button>
                {blurbs.map((b, i) => (
                  <div key={i} className="p-4 rounded-lg border bg-muted/30">
                    <p className="text-xs text-muted-foreground mb-1">版本 {i + 1}</p>
                    <p className="text-sm leading-relaxed">{b}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* 3. 钩子检测 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Target className="h-5 w-5" />开篇 & 章节钩子检测</CardTitle>
                <CardDescription>检查前200字是否有强冲突/悬念，以及每章结尾是否留了钩子。平台算法核心指标。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm">章节号：</span>
                  <Input type="number" value={hookChapterNum} onChange={e => setHookChapterNum(+e.target.value)} className="w-20" min={1} />
                  <Button onClick={handleHookCheck} disabled={platformLoading === "hook"} variant="outline">
                    {platformLoading === "hook" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Target className="h-4 w-4 mr-2" />}
                    检测开篇钩子
                  </Button>
                  <Button onClick={handleGenChapterTitle} disabled={platformLoading === "chapterTitle"} variant="outline">
                    {platformLoading === "chapterTitle" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileEdit className="h-4 w-4 mr-2" />}
                    生成章节标题
                  </Button>
                  <Separator orientation="vertical" className="h-8" />
                  <Button onClick={handleBatchHookCheck} disabled={platformLoading === "batch"} variant="outline">
                    {platformLoading === "batch" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    批量检测所有章节结尾钩子
                  </Button>
                </div>

                {hookResult && (
                  <div className="p-4 rounded-lg border space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">评分：</span>
                      <Badge variant={hookResult.score >= 7 ? "default" : "destructive"}>{hookResult.score}/10</Badge>
                      <Badge variant="outline">{hookResult.hook_strength}</Badge>
                    </div>
                    {hookResult.issues?.length > 0 && (
                      <div className="text-sm text-muted-foreground">
                        <span className="text-destructive font-medium">问题：</span>
                        {hookResult.issues.map((issue: string, i: number) => (
                          <p key={i} className="ml-2">- {issue}</p>
                        ))}
                      </div>
                    )}
                    {hookResult.rewrite_suggestion && <p className="text-sm">建议：{hookResult.rewrite_suggestion}</p>}
                    {hookResult.rewritten_opening && (
                      <div className="p-3 rounded bg-muted/50 text-sm">
                        <p className="text-xs text-muted-foreground mb-1">改写示例：</p>
                        <p>{hookResult.rewritten_opening}</p>
                      </div>
                    )}
                  </div>
                )}

                {chapterTitles.length > 0 && (
                  <div className="space-y-1 p-3 rounded-lg border bg-muted/30">
                    <p className="text-xs text-muted-foreground mb-2">章节标题候选：</p>
                    {chapterTitles.map((t, i) => <p key={i} className="text-sm">「{t}」</p>)}
                  </div>
                )}

                {batchHookResult.length > 0 && (
                  <div className="space-y-2 max-h-64 overflow-auto">
                    <p className="text-sm font-medium">批量检测结果：</p>
                    {batchHookResult.map((r: any) => (
                      <div key={r.chapter_number} className="flex items-center gap-3 p-2 rounded border text-sm">
                        <span className="font-mono">第{r.chapter_number}章</span>
                        <Badge variant={r.has_hook ? "default" : "destructive"}>{r.has_hook ? "有钩子" : "缺钩子"}</Badge>
                        {r.hook_type && <span className="text-muted-foreground">{r.hook_type}</span>}
                        {r.suggestion && <span className="text-muted-foreground text-xs truncate">{r.suggestion}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 4. 标签生成 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Tag className="h-5 w-5" />平台标签 & 关键词</CardTitle>
                <CardDescription>生成适配平台搜索算法的标签和关键词，提升搜索曝光</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={handleGenTags} disabled={platformLoading === "tags"}>
                  {platformLoading === "tags" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                  生成标签
                </Button>
                {tagsResult && (
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-medium mb-2">主标签：</p>
                      <div className="flex flex-wrap gap-2">
                        {tagsResult.main_tags?.map((t: string, i: number) => <Badge key={i} className="cursor-default">{t}</Badge>)}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium mb-2">搜索关键词：</p>
                      <div className="flex flex-wrap gap-2">
                        {tagsResult.search_keywords?.map((k: string, i: number) => <Badge key={i} variant="secondary" className="cursor-default">{k}</Badge>)}
                      </div>
                    </div>
                    {tagsResult.category_recommendation && <p className="text-sm">推荐分类：<span className="font-medium">{tagsResult.category_recommendation}</span></p>}
                    {tagsResult.target_audience && <p className="text-sm text-muted-foreground">目标读者：{tagsResult.target_audience}</p>}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader><CardTitle>项目参数</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label>目标平台</Label>
                  <Select value={config?.platform || "tomato"} onValueChange={(v) => updateConfig.mutate({ platform: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {PLATFORMS.map((key) => (
                        <SelectItem key={key} value={key}>
                          {PLATFORM_CONFIG[key].icon} {PLATFORM_CONFIG[key].label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>分类</Label>
                  <Input defaultValue={config?.category} onBlur={e => debouncedUpdate({ category: e.target.value })} />
                </div>
                <div>
                  <Label>类型</Label>
                  <Input defaultValue={config?.genre} onBlur={e => debouncedUpdate({ genre: e.target.value })} />
                </div>
                <div>
                  <Label>主题</Label>
                  <Input defaultValue={config?.topic} onBlur={e => debouncedUpdate({ topic: e.target.value })} />
                </div>
                <div>
                  <Label>章节数</Label>
                  <Input type="number" defaultValue={config?.num_chapters} onBlur={e => debouncedUpdate({ num_chapters: +e.target.value })} />
                </div>
                <div>
                  <Label>每章字数</Label>
                  <Input type="number" defaultValue={config?.word_number} onBlur={e => debouncedUpdate({ word_number: +e.target.value })} />
                </div>
              </div>
              <div>
                <Label>内容指导（大纲）</Label>
                <Textarea
                  defaultValue={config?.user_guidance}
                  rows={8}
                  onBlur={e => debouncedUpdate({ user_guidance: e.target.value })}
                  placeholder="在这里描述你的大纲、世界观、角色构想..."
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认清空向量库</DialogTitle>
            <DialogDescription>
              此操作将删除所有已导入的知识库向量数据，不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={handleClearVector}>确认清空</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={charDialogOpen} onOpenChange={(v) => { if (!v) { setCharDialogOpen(false); setEditChar(null) } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editChar ? "编辑角色" : "新增角色"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>角色名称</Label>
              <Input value={charName} onChange={e => setCharName(e.target.value)} placeholder="例如：主角名字" />
            </div>
            <div>
              <Label>描述</Label>
              <Textarea value={charDesc} onChange={e => setCharDesc(e.target.value)} rows={4} placeholder="角色的外貌、性格、背景故事等" />
            </div>
            <Button className="w-full" onClick={editChar ? handleUpdateCharacter : handleCreateCharacter} disabled={!charName.trim()}>
              {editChar ? "保存修改" : "创建"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteCharTarget !== null} onOpenChange={(v) => { if (!v) setDeleteCharTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除角色</DialogTitle>
            <DialogDescription>此操作不可撤销。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteCharTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteCharacter}>确认删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
