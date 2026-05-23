"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  Play, Save, CheckCircle, AlertCircle, Loader2, Wand2, 
  ListChecks, RefreshCw, Ban, Upload, Target, Eye, FileEdit, Gauge 
} from "lucide-react"
import React from "react"
import { useProjectContext } from "./ProjectContext"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import type { Chapter } from "@/lib/types"

export function WorkbenchTab() {
  const {
    projectId,
    chapters,
    updateConfig,
    batchUploading,
    setBatchUploading,
    batchFileRef,
    refetchChapters,
    generation: {
      generationTaskId, generationStopping, sseAction, isConnected, events, sseError,
      generationChapterCount, setGenerationChapterCount,
      generationWordCount, setGenerationWordCount,
      batchChapterCount, setBatchChapterCount,
      handleStopGeneration, startTask
    },
    workbench: {
      selectedChapterNumber, setSelectedChapterNumber,
      chapterEditorContent, setChapterEditorContent,
      chapterEditorLoading, chapterEditorSaving,
      activeChapterMeta, saveWorkbenchChapter, loadWorkbenchChapter
    },
    platform: {
      platformLoading, chapterTitles, hookResult, chapterHookResult, diagnosisResult,
      setHookChapterNum, handleGenSelectedChapterTitle, handleWorkbenchOpeningHook,
      handleWorkbenchEndingHook, handleDiagnoseChapter
    }
  } = useProjectContext()

  const completedChapters = chapters?.filter((c: Chapter) => c.status === "final").length || 0
  const draftChapters = chapters?.filter((c: Chapter) => c.status === "draft").length || 0
  const pendingChapters = chapters?.filter((c: Chapter) => c.status === "pending").length || 0
  const totalWords = chapters?.reduce((acc: number, cur: Chapter) => acc + (cur.word_count || 0), 0) || 0

  const selectedChapterFromList = chapters?.find((c: Chapter) => c.chapter_number === selectedChapterNumber)

  // -- Handlers --
  const handleApplyGenerationTargets = () => {
    updateConfig.mutate({
      num_chapters: generationChapterCount,
      word_number: generationWordCount,
    }, { onSuccess: () => toast.success("保存生成控制成功") })
  }

  const handleGenerateArchitecture = async () => {
    try {
      const { task_id } = await api.generate.architecture(projectId) as any
      startTask("architecture", `/api/v1/projects/${projectId}/generate/architecture`, task_id)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateBlueprint = async () => {
    try {
      const { task_id } = await api.generate.blueprint(projectId) as any
      startTask("blueprint", `/api/v1/projects/${projectId}/generate/blueprint`, task_id)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateWorkbenchChapter = async () => {
    try {
      const { task_id } = await api.generate.chapter(projectId, selectedChapterNumber) as any
      startTask("chapter", `/api/v1/projects/${projectId}/generate/chapter/${selectedChapterNumber}`, task_id)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateChapterBatch = async () => {
    try {
      const { task_id } = await api.generate.chapterBatch(projectId, selectedChapterNumber, batchChapterCount) as any
      startTask("chapterBatch", `/api/v1/projects/${projectId}/generate/chapters?start_chapter=${selectedChapterNumber}&count=${batchChapterCount}`, task_id)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleFinalizeWorkbenchChapter = async () => {
    if (!chapterEditorContent.trim()) return
    await saveWorkbenchChapter()
    try {
      const { task_id } = await api.generate.finalize(projectId, selectedChapterNumber) as any
      startTask("finalize", `/api/v1/projects/${projectId}/generate/finalize/${selectedChapterNumber}`, task_id)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleBatchUploadChapters = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setBatchUploading(true)
    try {
      await api.chapters.upload(projectId, Array.from(files))
      toast.success(`成功导入 ${files.length} 个章节`)
      refetchChapters()
    } catch (error) {
      toast.error((error as Error).message || "导入章节失败")
    } finally {
      setBatchUploading(false)
      if (batchFileRef.current) batchFileRef.current.value = ""
    }
  }

  // Effect to load chapter when selected changes
  React.useEffect(() => {
    loadWorkbenchChapter(selectedChapterNumber)
  }, [selectedChapterNumber])

  // Get the last partial event for streaming draft content
  const lastPartial = events.filter((e: any) => e.type === "partial").pop()

  // Stream text into editor during generation
  React.useEffect(() => {
    if ((sseAction === "chapter" || sseAction === "chapterBatch") && lastPartial?.data?.content) {
      if (lastPartial.data.step === "draft" || lastPartial.data.step === "voice_polish" || lastPartial.data.step === "quality_rewrite") {
        setChapterEditorContent(lastPartial.data.content)
      }
    }
  }, [lastPartial, sseAction])

  // Reload chapter text and meta when generation finishes
  React.useEffect(() => {
    if (events.length > 0) {
      const lastEvent = events[events.length - 1]
      if (lastEvent.type === "done" && (sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize")) {
        loadWorkbenchChapter(selectedChapterNumber)
        refetchChapters()
      }
    }
  }, [events, sseAction, selectedChapterNumber])

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base font-bold text-gradient-primary w-fit">
            <Gauge className="h-5 w-5 text-primary" />生成控制
          </CardTitle>
          <CardDescription>控制架构、目录和章节草稿的生成规模</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[150px_150px_150px_150px_minmax(0,1fr)]">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">总章节</Label>
              <Input
                type="number"
                min={1}
                value={generationChapterCount}
                onChange={(event) => setGenerationChapterCount(Math.max(1, Number(event.target.value) || 1))}
                className="bg-background/50"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">每章字数</Label>
              <Input
                type="number"
                min={500}
                step={500}
                value={generationWordCount}
                onChange={(event) => setGenerationWordCount(Math.max(500, Number(event.target.value) || 500))}
                className="bg-background/50"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">当前章节</Label>
              <Input
                type="number"
                min={1}
                max={generationChapterCount || undefined}
                value={selectedChapterNumber}
                onChange={(event) => {
                  const value = Math.max(1, Number(event.target.value) || 1)
                  setSelectedChapterNumber(value)
                  setHookChapterNum(value)
                }}
                className="bg-background/50"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">本轮章数</Label>
              <Input
                type="number"
                min={1}
                max={20}
                value={batchChapterCount}
                onChange={(event) => setBatchChapterCount(Math.min(20, Math.max(1, Number(event.target.value) || 1)))}
                className="bg-background/50"
              />
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <Button 
                variant="outline" 
                onClick={handleApplyGenerationTargets} 
                disabled={updateConfig.isPending}
                className="bg-card/40 border-border/80"
              >
                {updateConfig.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2 text-indigo-400" />}
                保存控制
              </Button>
              <Button 
                onClick={handleGenerateArchitecture} 
                disabled={isConnected || Boolean(generationTaskId) || generationStopping}
                className="shadow-md shadow-primary/10"
              >
                <Wand2 className="h-4 w-4 mr-2" />生成架构
              </Button>
              <Button 
                onClick={handleGenerateBlueprint} 
                disabled={isConnected || Boolean(generationTaskId) || generationStopping} 
                variant="outline"
                className="bg-card/40 border-border/80"
              >
                <ListChecks className="h-4 w-4 mr-2 text-purple-400" />生成目录
              </Button>
              <Button 
                onClick={handleGenerateWorkbenchChapter} 
                disabled={isConnected || Boolean(generationTaskId) || generationStopping} 
                variant="outline"
                className="bg-card/40 border-border/80"
              >
                <Play className="h-4 w-4 mr-2 text-emerald-400" />生成本章
              </Button>
              <Button 
                onClick={handleGenerateChapterBatch} 
                disabled={isConnected || Boolean(generationTaskId) || generationStopping} 
                variant="outline"
                className="bg-card/40 border-border/80"
              >
                <RefreshCw className="h-4 w-4 mr-2 text-blue-400" />批量生成
              </Button>
              {generationTaskId && (
                <Button variant="destructive" onClick={handleStopGeneration} disabled={generationStopping}>
                  {generationStopping ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Ban className="h-4 w-4 mr-2" />}
                  中断生成
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        {/* Left Side: Chapter List */}
        <Card className="glass-panel border-border/40 h-fit hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-bold text-gradient-primary w-fit">章节目录</CardTitle>
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  ref={batchFileRef}
                  className="hidden"
                  multiple
                  accept=".txt"
                  onChange={handleBatchUploadChapters}
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={batchUploading}
                  onClick={() => batchFileRef.current?.click()}
                  className="h-8 text-xs bg-card/40 border-border/80"
                >
                  {batchUploading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Upload className="h-3 w-3 mr-1" />}
                  导入章节
                </Button>
              </div>
            </div>
            <CardDescription className="text-xs">
              {completedChapters} 定稿 / {draftChapters} 草稿 / {pendingChapters} 待写
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {!chapters?.length ? (
              <div className="px-4 pb-6 text-sm text-muted-foreground">尚未生成章节目录</div>
            ) : (
              <ScrollArea className="h-[64vh] pr-2">
                <div className="space-y-1 p-2">
                  {chapters.map((chapter: Chapter) => (
                    <button
                      key={chapter.chapter_number}
                      type="button"
                      onClick={() => {
                        setSelectedChapterNumber(chapter.chapter_number)
                        setHookChapterNum(chapter.chapter_number)
                      }}
                      className={`w-full rounded-xl px-3 py-2.5 text-left transition-all duration-200 border ${
                        selectedChapterNumber === chapter.chapter_number
                          ? "bg-primary/10 border-primary/20 text-primary font-semibold shadow-inner"
                          : "hover:bg-accent/40 border-transparent hover:translate-x-0.5"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[10px] bg-secondary/80 px-1.5 py-0.5 rounded-md text-muted-foreground">
                          第{chapter.chapter_number}章
                        </span>
                        <Badge
                          variant={chapter.status === "final" ? "default" : chapter.status === "draft" ? "secondary" : "outline"}
                          className={`text-[10px] px-1.5 py-0 ${
                            chapter.status === "final"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : chapter.status === "draft"
                              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                              : "bg-secondary text-muted-foreground"
                          }`}
                        >
                          {chapter.status === "final" ? "定稿" : chapter.status === "draft" ? "草稿" : "待写"}
                        </Badge>
                      </div>
                      <p className="mt-1.5 truncate text-sm leading-tight">{chapter.chapter_title || "未命名"}</p>
                      {chapter.word_count > 0 && <p className="mt-1 text-[10px] text-muted-foreground">{chapter.word_count} 字</p>}
                    </button>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Center Pane: Editor */}
        <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
          <CardHeader className="border-b border-border/30 pb-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <CardTitle className="truncate text-lg font-bold">
                  第{selectedChapterNumber}章 {activeChapterMeta?.chapter_title || selectedChapterFromList?.chapter_title || ""}
                </CardTitle>
                <CardDescription className="truncate text-xs mt-1 max-w-[500px]">
                  {activeChapterMeta?.chapter_summary || selectedChapterFromList?.chapter_summary || "章节内容编辑区"}
                </CardDescription>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge
                  variant={activeChapterMeta?.status === "final" ? "default" : activeChapterMeta?.status === "draft" ? "secondary" : "outline"}
                  className={
                    activeChapterMeta?.status === "final"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : activeChapterMeta?.status === "draft"
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      : "bg-secondary text-muted-foreground"
                  }
                >
                  {activeChapterMeta?.status === "final" ? "已定稿" : activeChapterMeta?.status === "draft" ? "草稿" : "待生成"}
                </Badge>
                <Badge variant="outline" className="border-border bg-card/50">
                  {activeChapterMeta?.word_count || chapterEditorContent.length || 0} 字
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && isConnected && (
              <div className="flex items-center gap-2 rounded-xl bg-primary/10 border border-primary/20 p-3 text-sm text-primary animate-glow-pulse relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/20 to-transparent -translate-x-[100%] animate-[shimmer_2s_infinite]" />
                <Loader2 className="h-4 w-4 animate-spin shrink-0" />
                <span>AI 正在处理第{selectedChapterNumber}章...</span>
              </div>
            )}
            {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") &&
              events.filter(e => e.type === "progress").slice(-3).map((event, index) => (
                <div key={`${event.data.step}-${index}`} className="flex items-start gap-2 rounded-xl bg-muted/40 border border-border/50 p-2.5 text-xs">
                  {event.data.status === "done" ? (
                    <CheckCircle className="mt-0.5 h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Loader2 className="mt-0.5 h-3.5 w-3.5 animate-spin text-primary shrink-0" />
                  )}
                  <span>{event.data.message}</span>
                </div>
              ))}
            {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && sseError && (
              <div className="flex items-start gap-2 rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{sseError || "生成失败"}</span>
              </div>
            )}

            {chapterEditorLoading ? (
              <div className="space-y-3 py-6">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-[52vh] w-full rounded-xl" />
              </div>
            ) : (
              <Textarea
                value={chapterEditorContent}
                onChange={(event) => setChapterEditorContent(event.target.value)}
                className="min-h-[52vh] resize-none font-serif text-base md:text-lg leading-8 tracking-wider p-4 bg-background/30 focus-visible:ring-primary/25 border-border/80 rounded-xl transition-all"
                placeholder="在这里生成、编辑、保存章节草稿..."
              />
            )}

            <div className="flex flex-wrap gap-2 pt-2">
              <Button onClick={saveWorkbenchChapter} disabled={chapterEditorSaving || chapterEditorLoading}>
                {chapterEditorSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2 text-primary-foreground" />}
                保存草稿
              </Button>
              <Button variant="outline" onClick={handleGenerateWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping} className="hover:bg-accent/40">
                <Play className="h-4 w-4 mr-2 text-emerald-400" />AI 生成本章
              </Button>
              <Button variant="secondary" onClick={handleFinalizeWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping || !chapterEditorContent.trim()} className="hover:bg-accent/50">
                <CheckCircle className="h-4 w-4 mr-2 text-indigo-400" />定稿
              </Button>
              {generationTaskId && (
                <Button variant="destructive" onClick={handleStopGeneration} disabled={generationStopping}>
                  {generationStopping ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Ban className="h-4 w-4 mr-2" />}
                  中断生成
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right Pane: Info & Diagnoses */}
        <div className="space-y-6">
          <Card className="glass-panel border-border/40">
            <CardHeader className="pb-3 border-b border-border/30">
              <CardTitle className="text-sm font-bold">章节大纲属性</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3.5 text-xs pt-4">
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground shrink-0">章节定位：</span>
                <span className="font-semibold text-right">{activeChapterMeta?.chapter_role || "-"}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground shrink-0">核心作用：</span>
                <span className="font-semibold text-right">{activeChapterMeta?.chapter_purpose || "-"}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground shrink-0">悬念密度：</span>
                <span className="font-semibold text-right">{activeChapterMeta?.suspense_level || "-"}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground shrink-0">伏笔操作：</span>
                <span className="font-semibold text-right">{activeChapterMeta?.foreshadowing || "-"}</span>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground shrink-0">认知颠覆：</span>
                <span className="font-semibold text-right">{activeChapterMeta?.plot_twist_level || "-"}</span>
              </div>
              <Separator className="bg-border/30" />
              <div className="flex items-center justify-between text-muted-foreground text-[10px]">
                <span>项目总字数：</span>
                <span className="font-semibold text-sm text-foreground">{totalWords} 字</span>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-panel border-border/40">
            <CardHeader className="pb-3 border-b border-border/30">
              <CardTitle className="text-sm font-bold">平台辅助质检</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-4">
              <Button className="w-full justify-start text-xs bg-card/30 border-border/80" variant="outline" onClick={() => handleWorkbenchOpeningHook(1)} disabled={platformLoading === "workbenchOpening"}>
                {platformLoading === "workbenchOpening" ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> : <Target className="h-3.5 w-3.5 mr-2 text-indigo-400" />}
                检测开篇抓力
              </Button>
              <Button className="w-full justify-start text-xs bg-card/30 border-border/80" variant="outline" onClick={() => handleWorkbenchEndingHook(selectedChapterNumber)} disabled={platformLoading === "workbenchEnding"}>
                {platformLoading === "workbenchEnding" ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> : <Eye className="h-3.5 w-3.5 mr-2 text-emerald-400" />}
                检测结尾钩子
              </Button>
              <Button className="w-full justify-start text-xs bg-card/30 border-border/80" variant="outline" onClick={() => handleGenSelectedChapterTitle(selectedChapterNumber)} disabled={platformLoading === "workbenchTitle"}>
                {platformLoading === "workbenchTitle" ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> : <FileEdit className="h-3.5 w-3.5 mr-2 text-blue-400" />}
                生成章节标题
              </Button>

              {chapterTitles.length > 0 && (
                <div className="space-y-1.5 rounded-xl border border-border/50 bg-secondary/30 p-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 font-semibold">标题候选</p>
                  {chapterTitles.map((title, index) => <p key={index} className="text-xs leading-tight font-medium">「{title}」</p>)}
                </div>
              )}
              {hookResult && (
                <div className="space-y-2 rounded-xl border border-border/50 p-3 text-xs bg-card/10">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">开篇评分</span>
                    <Badge variant={(hookResult.score || 0) >= 7 ? "default" : "destructive"} className={(hookResult.score || 0) >= 7 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-destructive/10 text-destructive border-destructive/20"}>{hookResult.score}/10</Badge>
                  </div>
                  {hookResult.rewrite_suggestion && <p className="text-muted-foreground leading-relaxed mt-1 text-[11px]">{hookResult.rewrite_suggestion}</p>}
                </div>
              )}
              {chapterHookResult && (
                <div className="space-y-2 rounded-xl border border-border/50 p-3 text-xs bg-card/10">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">结尾钩子</span>
                    <Badge variant={chapterHookResult.has_hook ? "default" : "destructive"} className={chapterHookResult.has_hook ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-destructive/10 text-destructive border-destructive/20"}>
                      {chapterHookResult.has_hook ? "符合标准" : "需要加强"}
                    </Badge>
                  </div>
                  {chapterHookResult.suggestion && <p className="text-muted-foreground leading-relaxed mt-1 text-[11px]">{chapterHookResult.suggestion}</p>}
                </div>
              )}

              <Separator className="bg-border/30" />
              <Button className="w-full justify-start text-xs bg-card/30 border-border/80" variant="outline" onClick={() => handleDiagnoseChapter(selectedChapterNumber)} disabled={platformLoading === "diagnosis"}>
                {platformLoading === "diagnosis" ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> : <Gauge className="h-3.5 w-3.5 mr-2 text-amber-400" />}
                诊断本章文风质量
              </Button>

              {diagnosisResult && (
                <div className="space-y-2 rounded-xl border border-border/50 bg-secondary/20 p-3 text-xs max-h-72 overflow-auto pr-1">
                  <p className="text-[10px] text-muted-foreground uppercase font-semibold mb-1 border-b border-border/30 pb-1">文风质检诊断</p>
                  {diagnosisResult.split("\n").map((line, index) => {
                    const isHeader = line.startsWith("【")
                    if (isHeader) {
                      return <p key={index} className="font-bold text-xs mt-2.5 mb-1 text-primary">{line}</p>
                    }
                    if (line.trim()) {
                      return <p key={index} className="leading-relaxed text-muted-foreground text-[11px]">{line}</p>
                    }
                    return <div key={index} className="h-1" />
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
