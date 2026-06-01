"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { 
  Loader2, Gauge, AlertCircle, Ban, CheckCircle, RefreshCcw, Sparkles, Info,
  BookOpen, Users, Search, ShieldAlert, Wand2, Send, ClipboardList, History, FileText, Check, Edit,
  MessageSquare, ChevronsLeft, Settings
} from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { useProjectContext } from "../ProjectContext"
import type { Chapter, PlatformDiagnosisItem } from "@/lib/types"
import { parseDiagnosisItems } from "@/lib/types"
import { DiagnosisFixDialog } from "./DiagnosisFixDialog"
import { toast } from "sonner"

export function WorkbenchStatusPane({ isDrawer = false }: { isDrawer?: boolean }) {
  const {
    projectId,
    project,
    chapters,
    config,
    generation: {
      generationTaskId, generationStopping, generationTaskLabel, generationProgress,
      isConnected, events, sseError, sseAction, generationStepMeta,
      batchChapterIndex, batchTotalChapters,
      handleStopGeneration, handleRetryGeneration
    },
    workbench: {
      selectedChapterNumber,
      activeChapterMeta,
      chapterEditorContent,
      setChapterEditorContent,
      selectedText, setSelectedText,
      isRewriting,
      assistantMode, setAssistantMode,
      sidebarTab, setSidebarTab,
      selectionDiagnosis, setSelectionDiagnosis,
      selectionDiagLoading, setSelectionDiagLoading,
      rewritePreview, setRewritePreview,
      customRewriteInstruction, setCustomRewriteInstruction,
      assistantChatHistory, setAssistantChatHistory,
      assistantQuestion, setAssistantQuestion,
      assistantChatLoading, setAssistantChatLoading,
      handleDiagnoseSelection,
      handleRewriteSelection,
      handleApplyRewrite,
      handleAssistantChat,
      handleAskAi,
      chatHistory, setChatHistory,
      aiQuestion, setAiQuestion,
      askAiLoading, setAskAiLoading,
      rightPanelOpen, setRightPanelOpen,
      layoutMode, setLayoutMode,
      rightPanelCollapsed, setRightPanelCollapsed,
      assistantDrawerOpen, setAssistantDrawerOpen,
      activeAssistantTool, setActiveAssistantTool
    },
    platform: {
      platformLoading, chapterTitles, hookResult, chapterHookResult, diagnosisResult,
      handleGenSelectedChapterTitle, handleWorkbenchOpeningHook,
      handleWorkbenchEndingHook, handleDiagnoseChapter
    }
  } = useProjectContext()

  const [diagnosisItems, setDiagnosisItems] = useState<PlatformDiagnosisItem[]>([])
  const [selectedFixIssues, setSelectedFixIssues] = useState<string[]>([])
  const [fixDialogOpen, setFixDialogOpen] = useState(false)
  const [subMode, setSubMode] = useState<"diagnose" | "rewrite" | "chat">("diagnose")

  const currentWordCount = chapterEditorContent?.length || activeChapterMeta?.word_count || 0
  const targetWordCount = config?.word_number || 3000
  const wordCountPercent = targetWordCount > 0 ? (currentWordCount / targetWordCount) * 100 : 0

  // Word count calculations
  const totalWords = chapters?.reduce((acc: number, cur: Chapter) => acc + (cur.word_count || 0), 0) || 0
  const totalChapters = chapters?.length || 0
  
  // Completed chapters
  const completedChapters = chapters?.filter((c: Chapter) => c.status === "final").length || 0
  
  // Creation days calculation
  const createdDate = project?.created_at ? new Date(project.created_at) : new Date()
  const diffTime = Math.abs(new Date().getTime() - createdDate.getTime())
  const creationDays = Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)))

  React.useEffect(() => {
    if (diagnosisResult) {
      const items = parseDiagnosisItems(diagnosisResult)
      setDiagnosisItems(items)
      setSelectedFixIssues(items.filter(i => i.autoFixable).map(i => i.type))
    } else {
      setDiagnosisItems([])
      setSelectedFixIssues([])
    }
  }, [diagnosisResult])

  const progressEvents = events.filter((e: any) => e.type === "progress")

  // Collapsed 56px tool rail view for wide/collapsed mode
  if (!isDrawer && (layoutMode === "wide" || rightPanelCollapsed)) {
    const tools = [
      { id: "outline", label: "大纲参考", icon: BookOpen },
      { id: "chat", label: "询问 AI", icon: MessageSquare },
      { id: "assistant", label: "写作助手", icon: Sparkles },
      { id: "characters", label: "角色分析", icon: Users },
      { id: "plot", label: "情节分析", icon: ClipboardList },
      { id: "settings", label: "设置中心", icon: Settings },
    ]

    return (
      <div className="w-14 bg-[#0b0f1a]/80 border border-white/5 rounded-2xl h-full flex flex-col items-center py-4 gap-6 hover:shadow-[0_0_30px_rgba(139,92,246,0.05)] transition-all duration-500">
        {/* Toggle drawer button */}
        <button
          type="button"
          onClick={() => setAssistantDrawerOpen(true)}
          className="p-2.5 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all cursor-pointer"
          title="展开 AI 助手 (抽屉)"
        >
          <Sparkles className="h-5 w-5 text-indigo-400 animate-pulse" />
        </button>

        {/* Divider */}
        <div className="w-8 h-[1px] bg-white/5 my-1" />

        {/* Tool buttons list */}
        <div className="flex-1 flex flex-col items-center gap-3">
          {tools.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  if (t.id === "outline" || t.id === "chat" || t.id === "assistant") {
                    setSidebarTab(t.id)
                  } else if (t.id === "characters") {
                    setSidebarTab("chat")
                    handleAskAi("请分析本章中所有出场人物的性格塑造、心理活动、言行反应与人设一致性，并指出是否有逻辑瑕疵。")
                  } else if (t.id === "plot") {
                    setSidebarTab("chat")
                    handleAskAi("请对当前章节进行详细的情节逻辑、矛盾冲突、悬念张力和情节节奏分析，指出优缺点和改进建议。")
                  } else if (t.id === "settings") {
                    toast.info("即将支持快捷参数设置")
                  }
                  setAssistantDrawerOpen(true)
                }}
                className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all cursor-pointer relative"
                title={t.label}
              >
                <Icon className="h-5 w-5" />
              </button>
            )
          })}
        </div>

        {/* Expand right panel button */}
        <button
          type="button"
          onClick={() => {
            setRightPanelCollapsed(false)
            if (layoutMode === "wide") {
              setLayoutMode("standard")
              localStorage.setItem("ai-novel-workbench-layout-mode-user-select", "standard")
            }
          }}
          className="p-2.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all mt-auto cursor-pointer"
          title="展开右侧面板"
        >
          <ChevronsLeft className="h-5 w-5" />
        </button>
      </div>
    )
  }

  return (
    <div className={`space-y-4 h-full overflow-y-auto ${isDrawer ? 'px-2' : 'pr-1'} pb-4 flex flex-col min-w-0 workbench-scrollbar`}>
      {/* 生成进度卡片 - 有活跃任务时显示 */}
      {(isConnected || generationTaskId) && (
        <Card className="glass-panel border-primary/30 bg-primary/5 shadow-lg shadow-primary/5 shrink-0 animate-glow-pulse">
          <CardHeader className="pb-2 px-4 border-b border-primary/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-bold flex items-center gap-2 text-primary">
                <Sparkles className="h-3.5 w-3.5" />
                生成进度
              </CardTitle>
              <Badge
                variant={generationStopping ? "secondary" : "outline"}
                className={
                  generationStopping
                    ? "bg-secondary text-muted-foreground text-[10px] px-1.5 py-0"
                    : isConnected
                    ? "bg-primary/10 text-primary border-primary/20 text-[10px] px-1.5 py-0"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px] px-1.5 py-0"
                }
              >
                {generationStopping ? "停止中" : isConnected ? "进行中" : "后台继续中"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-3 px-4 text-xs">
            <p className="font-semibold text-foreground truncate">{generationTaskLabel || "准备中..."}</p>

            {/* Batch chapter progress */}
            {sseAction === "chapterBatch" && batchChapterIndex > 0 && (
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span className="font-mono text-primary font-semibold">
                  第 {batchChapterIndex}/{batchTotalChapters} 章
                </span>
                <span>生成中</span>
              </div>
            )}

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>完成进度</span>
                <span className="font-mono text-primary">{generationProgress}%</span>
              </div>
              <Progress value={generationProgress} className="w-full h-1.5 [&_[data-slot=progress-indicator]]:bg-primary" />
            </div>

            {/* Recent progress events */}
            {progressEvents.length > 0 && (
              <div className="space-y-1 max-h-24 overflow-y-auto pr-1">
                {progressEvents.slice(-4).map((event: any, i: number) => {
                  const meta = generationStepMeta(event.data?.step)
                  return (
                    <div key={i} className="flex items-start gap-1.5 text-[10px]">
                      {event.data?.status === "done" ? (
                        <CheckCircle className="h-3 w-3 text-emerald-400 mt-0.5 shrink-0" />
                      ) : (
                        <Loader2 className="h-3 w-3 animate-spin text-primary mt-0.5 shrink-0" />
                      )}
                      <span className="text-muted-foreground leading-tight">
                        {event.data?.message || meta.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Error state */}
            {sseError && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-2 text-[10px] text-destructive space-y-1.5">
                <div className="flex items-start gap-1.5">
                  <AlertCircle className="h-3 w-3 mt-0.5 shrink-0" />
                  <span>{sseError}</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetryGeneration}
                  className="text-foreground h-6 text-[10px] w-full"
                >
                  <RefreshCcw className="w-2.5 h-2.5 mr-1" />
                  从断点重试
                </Button>
              </div>
            )}

            {/* Stop button */}
            {generationTaskId && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleStopGeneration}
                disabled={generationStopping}
                className="w-full h-7 text-[10px] bg-rose-600/20 hover:bg-rose-600/35 text-rose-300 border border-rose-500/30"
              >
                {generationStopping ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Ban className="h-3 w-3 mr-1" />}
                中断生成
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* 创作统计 */}
      <Card className="glass-panel border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.05)] transition-all duration-300 shrink-0">
        <CardHeader className="pb-1.5 pt-3 px-4 flex flex-row items-center justify-between">
          <CardTitle className="text-xs font-bold text-muted-foreground flex items-center gap-1.5">
            <ClipboardList className="h-3.5 w-3.5 text-indigo-400" />
            创作统计
          </CardTitle>
          <span className="text-[10px] text-muted-foreground font-mono">第 {selectedChapterNumber} 章</span>
        </CardHeader>
        <CardContent className="px-4 pb-3 pt-1 space-y-3">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-muted/15 border border-border/20 rounded-xl p-2">
              <span className="text-[10px] text-muted-foreground block mb-0.5">总字数</span>
              <span className="text-xs font-bold text-foreground font-mono">{totalWords.toLocaleString()}</span>
            </div>
            <div className="bg-muted/15 border border-border/20 rounded-xl p-2">
              <span className="text-[10px] text-muted-foreground block mb-0.5">总章节</span>
              <span className="text-xs font-bold text-foreground font-mono">{totalChapters} 章</span>
            </div>
            <div className="bg-muted/15 border border-border/20 rounded-xl p-2">
              <span className="text-[10px] text-muted-foreground block mb-0.5">创作天数</span>
              <span className="text-xs font-bold text-foreground font-mono">{creationDays} 天</span>
            </div>
          </div>
          
          <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>已定稿章节进度</span>
              <span className="font-mono text-primary font-semibold">{completedChapters} / {totalChapters} 章</span>
            </div>
            <Progress 
              value={totalChapters > 0 ? (completedChapters / totalChapters) * 100 : 0} 
              className="w-full h-1 [&_[data-slot=progress-indicator]]:bg-primary"
            />
          </div>
        </CardContent>
      </Card>

      {/* AI 助手 */}
      <Card className="glass-panel border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.05)] transition-all duration-300 flex-1 flex flex-col min-h-[360px] min-w-0">
        <CardHeader className="pb-1 px-4 pt-3 shrink-0">
          <CardTitle className="text-xs font-bold text-muted-foreground flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-violet-400 animate-pulse" />
            AI 助手
          </CardTitle>
        </CardHeader>
        <CardContent className="px-3 pb-3 flex-1 flex flex-col min-h-0">
          <Tabs value={sidebarTab} onValueChange={setSidebarTab} className="w-full flex-1 flex flex-col min-h-0">
            <TabsList className="grid grid-cols-3 h-8 p-0.5 bg-muted/40 rounded-lg shrink-0 mb-2">
              <TabsTrigger value="outline" className="text-[10px] py-1 rounded">大纲参考</TabsTrigger>
              <TabsTrigger value="chat" className="text-[10px] py-1 rounded">询问 AI</TabsTrigger>
              <TabsTrigger value="assistant" className="text-[10px] py-1 rounded">写作助手</TabsTrigger>
            </TabsList>
            
            {/* 大纲参考 */}
            <TabsContent value="outline" className="flex-1 overflow-y-auto space-y-3 pr-1 mt-0 text-xs focus-visible:ring-0">
              <div className="space-y-1 bg-muted/20 border border-border/30 rounded-lg p-2.5 text-xs">
                <p className="flex justify-between gap-2 py-0.5"><strong className="text-muted-foreground shrink-0">章节定位：</strong><span className="text-foreground text-right">{activeChapterMeta?.chapter_role || "未指定"}</span></p>
                <p className="flex justify-between gap-2 py-0.5"><strong className="text-muted-foreground shrink-0">核心作用：</strong><span className="text-foreground text-right">{activeChapterMeta?.chapter_purpose || "未指定"}</span></p>
                {activeChapterMeta?.chapter_summary && (
                  <div className="mt-2 pt-2 border-t border-border/10">
                    <strong className="text-muted-foreground block mb-0.5">目标剧情：</strong>
                    <p className="text-muted-foreground leading-relaxed text-[11px]">{activeChapterMeta.chapter_summary}</p>
                  </div>
                )}
              </div>

              {activeChapterMeta?.foreshadowing && (
                <div className="space-y-1">
                  <span className="text-[10px] text-muted-foreground font-semibold uppercase block px-0.5">伏笔悬念</span>
                  <div className="bg-muted/20 border border-border/30 rounded-lg p-2.5 text-xs text-muted-foreground leading-relaxed">
                    {activeChapterMeta.foreshadowing}
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <span className="text-[10px] text-muted-foreground font-semibold uppercase block px-0.5">配置要求</span>
                <div className="bg-muted/20 border border-border/30 rounded-lg p-2.5 space-y-1.5 text-xs">
                  {config?.topic && <p className="flex items-start gap-1"><strong className="text-muted-foreground shrink-0">主题设定：</strong><span className="text-foreground">{config.topic}</span></p>}
                  {config?.style_requirement && <p className="flex items-start gap-1"><strong className="text-muted-foreground shrink-0">文风要求：</strong><span className="text-foreground">{config.style_requirement}</span></p>}
                  {config?.forbidden && <p className="text-rose-400 flex items-start gap-1"><strong className="text-rose-400/70 shrink-0">避雷限制：</strong><span>{config.forbidden}</span></p>}
                </div>
              </div>
            </TabsContent>
            
            {/* 询问 AI */}
            <TabsContent value="chat" className="flex-1 flex flex-col min-h-0 mt-0 focus-visible:ring-0">
              <div className="flex-1 overflow-y-auto space-y-3 mb-2 pr-1 min-h-[140px]">
                {chatHistory.length === 0 ? (
                  <div className="text-center text-muted-foreground/60 py-10 space-y-2">
                    <AlertCircle className="h-6 w-6 mx-auto text-muted-foreground/30" />
                    <p className="text-xs">向 AI 提问本章的情节逻辑与写作设想。</p>
                    <p className="text-[10px] text-muted-foreground/40">如：“我想在这里加个冲突，该怎么铺垫？”</p>
                  </div>
                ) : (
                  chatHistory.map((msg, i) => (
                    <div key={i} className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      <div className="text-[9px] text-muted-foreground opacity-75 px-1">
                        {msg.role === 'user' ? '作者' : 'AI 写作助手'}
                      </div>
                      <div className={`p-2.5 rounded-xl text-xs max-w-[88%] leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-primary/20 text-foreground border border-primary/30 rounded-tr-none'
                          : 'bg-muted/40 text-foreground border border-border/50 rounded-tl-none'
                      }`}>
                        <div className="whitespace-pre-wrap">{msg.content || (askAiLoading && i === chatHistory.length - 1 ? "正在分析中..." : "")}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="shrink-0 space-y-2 mt-auto pt-2 border-t border-border/10 bg-background/50">
                {/* Presets */}
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    onClick={() => handleAskAi("分析当前章节的情节张力与节奏控制。")}
                    disabled={askAiLoading}
                    className="text-[9px] bg-muted/40 hover:bg-muted border border-border/40 rounded px-1.5 py-0.5 text-muted-foreground transition-colors"
                  >
                    🔥 节奏张力
                  </button>
                  <button
                    type="button"
                    onClick={() => handleAskAi("帮我检查这一章里的人物行为是否合逻辑？")}
                    disabled={askAiLoading}
                    className="text-[9px] bg-muted/40 hover:bg-muted border border-border/40 rounded px-1.5 py-0.5 text-muted-foreground transition-colors"
                  >
                    👤 行为逻辑
                  </button>
                </div>

                <div className="flex gap-1.5 items-end bg-background/30 rounded-lg p-1.5 border border-border/30">
                  <textarea
                    placeholder="向 AI 提问..."
                    value={aiQuestion}
                    onChange={(e) => setAiQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleAskAi(aiQuestion)
                      }
                    }}
                    rows={1}
                    className="flex-1 resize-none bg-transparent outline-none border-0 text-xs text-foreground placeholder-muted-foreground/60 p-1 min-h-[24px] max-h-[60px]"
                  />
                  <Button
                    size="icon"
                    onClick={() => handleAskAi(aiQuestion)}
                    disabled={askAiLoading || !aiQuestion.trim()}
                    className="h-7 w-7 rounded-md bg-primary hover:bg-primary/90 text-white shrink-0 shadow-sm"
                  >
                    {askAiLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* 写作助手 */}
            <TabsContent value="assistant" className="flex-1 flex flex-col min-h-0 mt-0 focus-visible:ring-0">
              <div className="mb-2 shrink-0">
                <span className="text-[10px] text-muted-foreground font-semibold uppercase block mb-1">选中片段</span>
                {selectedText ? (
                  <div className="bg-muted/30 border border-border/40 rounded-lg p-2 text-xs text-muted-foreground line-clamp-2 relative pr-8">
                    <span className="italic">&quot;{selectedText}&quot;</span>
                    <button 
                      onClick={() => setSelectedText("")} 
                      className="absolute top-2 right-2 text-muted-foreground hover:text-foreground text-[10px] font-bold"
                    >
                      ×
                    </button>
                  </div>
                ) : (
                  <div className="bg-muted/15 border border-dashed border-border/30 rounded-lg p-3 text-center text-xs text-muted-foreground">
                    <Info className="h-4 w-4 mx-auto text-muted-foreground/45 mb-1" />
                    请在正文中选中任意文字，即可在此处启动文风诊断与重写。
                  </div>
                )}
              </div>

              {selectedText && (
                <div className="flex-1 flex flex-col min-h-0">
                  <div className="flex border-b border-border/10 pb-1 mb-2 gap-1.5 shrink-0">
                    {(["diagnose", "rewrite", "chat"] as const).map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setSubMode(m)}
                        className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                          subMode === m
                            ? "bg-primary/20 text-primary font-medium"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                        }`}
                      >
                        {m === "diagnose" ? "文风诊断" : m === "rewrite" ? "AI 改写" : "教练对话"}
                      </button>
                    ))}
                  </div>
                  
                  <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[120px]">
                    {subMode === "diagnose" && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground font-semibold">诊断分析</span>
                          <Button
                            size="xs"
                            onClick={() => handleDiagnoseSelection()}
                            disabled={selectionDiagLoading}
                            className="h-6 text-[10px] bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 px-2 py-0"
                          >
                            {selectionDiagLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                            重新诊断
                          </Button>
                        </div>
                        
                        {selectionDiagnosis ? (
                          <div className="bg-card/30 border border-border/40 rounded-lg p-2.5 text-xs leading-relaxed text-foreground whitespace-pre-wrap">
                            {selectionDiagnosis}
                          </div>
                        ) : (
                          !selectionDiagLoading && (
                            <p className="text-[11px] text-muted-foreground text-center py-6">
                              点击“重新诊断”按钮分析所选文本的节奏、表达欠缺处。
                            </p>
                          )
                        )}
                      </div>
                    )}

                    {subMode === "rewrite" && (
                      <div className="space-y-2">
                        <div className="space-y-1">
                          <div className="flex gap-1.5">
                            <textarea
                              placeholder="输入改写要求，如：'更激烈一些'..."
                              value={customRewriteInstruction}
                              onChange={(e) => setCustomRewriteInstruction(e.target.value)}
                              className="flex-1 h-10 text-xs bg-background/40 border border-border/40 rounded-md p-1.5 focus:outline-none focus:ring-1 focus:ring-primary/40 text-foreground resize-none"
                            />
                            <Button
                              onClick={() => handleRewriteSelection(customRewriteInstruction)}
                              disabled={isRewriting || !customRewriteInstruction.trim()}
                              className="h-10 w-12 bg-primary hover:bg-primary/90 text-white shrink-0 text-[10px] rounded-md leading-tight"
                            >
                              {isRewriting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "改写"}
                            </Button>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-1">
                          {["润色句子", "丰富细节", "更具悬念", "精简文字"].map((preset) => (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => {
                                setCustomRewriteInstruction(preset)
                                handleRewriteSelection(preset)
                              }}
                              disabled={isRewriting}
                              className="text-[9px] bg-muted/40 hover:bg-muted/70 border border-border/40 rounded px-1.5 py-0.5 text-muted-foreground transition-colors"
                            >
                              {preset}
                            </button>
                          ))}
                        </div>

                        {rewritePreview && (
                          <div className="space-y-1.5 pt-1.5 border-t border-border/10">
                            <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                              <CheckCircle className="h-3 w-3" /> 改写预览
                            </span>
                            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-2 text-xs text-foreground leading-relaxed whitespace-pre-wrap">
                              {rewritePreview}
                            </div>
                            <Button
                              onClick={handleApplyRewrite}
                              className="w-full h-7 bg-emerald-600 hover:bg-emerald-700 text-white text-xs rounded-md shadow-md"
                            >
                              应用替换原文本
                            </Button>
                          </div>
                        )}
                      </div>
                    )}

                    {subMode === "chat" && (
                      <div className="flex flex-col space-y-2">
                        <div className="overflow-y-auto space-y-2 max-h-[140px] bg-muted/10 p-2 rounded-lg border border-border/20">
                          {assistantChatHistory.length === 0 ? (
                            <p className="text-[11px] text-muted-foreground text-center py-4">
                              询问小助手：“为什么这里这样写？”
                            </p>
                          ) : (
                            assistantChatHistory.map((msg, i) => (
                              <div key={i} className="space-y-0.5">
                                <span className="text-[9px] font-bold text-muted-foreground">
                                  {msg.role === 'user' ? '作者' : '写作教练'}：
                                </span>
                                <p className={`text-[11px] p-1.5 rounded leading-relaxed ${
                                  msg.role === 'user' ? 'bg-primary/10 text-foreground' : 'bg-card/50 text-foreground border border-border/20'
                                }`}>
                                  {msg.content || (assistantChatLoading && i === assistantChatHistory.length - 1 ? "正在思考中..." : "")}
                                </p>
                              </div>
                            ))
                          )}
                        </div>

                        <div className="flex gap-1.5 items-center">
                          <input
                            placeholder="输入问题..."
                            value={assistantQuestion}
                            onChange={(e) => setAssistantQuestion(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && assistantQuestion.trim() && !assistantChatLoading) {
                                handleAssistantChat(assistantQuestion)
                              }
                            }}
                            className="flex-1 h-7 text-xs bg-background/40 border border-border/40 rounded px-2 focus:outline-none focus:ring-1 focus:ring-primary/40 text-foreground"
                          />
                          <Button
                            size="sm"
                            onClick={() => handleAssistantChat(assistantQuestion)}
                            disabled={assistantChatLoading || !assistantQuestion.trim()}
                            className="h-7 text-[10px] px-2 bg-primary hover:bg-primary/90 text-white rounded-md shrink-0"
                          >
                            发送
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* 智能工具 */}
      <Card className="glass-panel border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.05)] transition-all duration-300 shrink-0">
        <CardHeader className="pb-1.5 pt-3 px-4">
          <CardTitle className="text-xs font-bold text-muted-foreground flex items-center gap-1.5">
            <Gauge className="h-3.5 w-3.5 text-amber-400" />
            智能工具
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-3 pt-1">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => {
                toast.info("已启动本章文风诊断...");
                handleDiagnoseChapter(selectedChapterNumber)
              }}
              className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/15 hover:bg-primary/10 hover:border-primary/30 p-2.5 transition-all text-left group"
            >
              <div className="rounded-lg bg-indigo-500/10 p-1.5 group-hover:bg-indigo-500/20 text-indigo-400 transition-colors">
                <Gauge className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-foreground block">文风诊断</span>
                <span className="text-[9px] text-muted-foreground block truncate">分析语调风格</span>
              </div>
            </button>

            <button
              onClick={() => {
                setSidebarTab("chat")
                toast.info("情节分析已启动，结果将在 AI 助手中显示。")
                handleAskAi("请对当前章节进行详细的情节逻辑、矛盾冲突、悬念张力和情节节奏分析，指出优缺点和改进建议。")
              }}
              className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/15 hover:bg-primary/10 hover:border-primary/30 p-2.5 transition-all text-left group"
            >
              <div className="rounded-lg bg-rose-500/10 p-1.5 group-hover:bg-rose-500/20 text-rose-400 transition-colors">
                <BookOpen className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-foreground block">情节分析</span>
                <span className="text-[9px] text-muted-foreground block truncate">解构叙事张力</span>
              </div>
            </button>

            <button
              onClick={() => {
                setSidebarTab("chat")
                toast.info("角色分析已启动，结果将在 AI 助手中显示。")
                handleAskAi("请分析本章中所有出场人物的性格塑造、心理活动、言行反应与人设一致性，并指出是否有逻辑瑕疵。")
              }}
              className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/15 hover:bg-primary/10 hover:border-primary/30 p-2.5 transition-all text-left group"
            >
              <div className="rounded-lg bg-blue-500/10 p-1.5 group-hover:bg-blue-500/20 text-blue-400 transition-colors">
                <Users className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-foreground block">角色分析</span>
                <span className="text-[9px] text-muted-foreground block truncate">剖析行为动机</span>
              </div>
            </button>

            <button
              onClick={() => {
                setSidebarTab("chat")
                toast.info("设定检索已启动，结果将在 AI 助手中显示。")
                handleAskAi("请对比本小说的世界观设定、背景设定、力量体系和人物关系设定，匹配本章正文中是否存在吃设定或前后矛盾的情况。")
              }}
              className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/15 hover:bg-primary/10 hover:border-primary/30 p-2.5 transition-all text-left group"
            >
              <div className="rounded-lg bg-amber-500/10 p-1.5 group-hover:bg-amber-500/20 text-amber-400 transition-colors">
                <Search className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-foreground block">设定检索</span>
                <span className="text-[9px] text-muted-foreground block truncate">验证吃设定风险</span>
              </div>
            </button>

            <button
              onClick={() => {
                setSidebarTab("chat")
                toast.info("敏感词检测已启动，结果将在 AI 助手中显示。")
                handleAskAi("请对本章内容进行合规性与暴力粗俗词句检测，列出可能存在的违规敏感词语和段落，并给出替换建议。")
              }}
              className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/15 hover:bg-primary/10 hover:border-primary/30 p-2.5 transition-all text-left group"
            >
              <div className="rounded-lg bg-emerald-500/10 p-1.5 group-hover:bg-emerald-500/20 text-emerald-400 transition-colors">
                <ShieldAlert className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-foreground block">敏感词检测</span>
                <span className="text-[9px] text-muted-foreground block truncate">扫描安全合规性</span>
              </div>
            </button>

            <button
              onClick={() => {
                setSidebarTab("chat")
                toast.info("续写建议已启动，结果将在 AI 助手中显示。")
                handleAskAi("请根据本章现有内容、剧情大纲和下一章的前景设想，提出 3 个下一步的续写情节走向及细节桥段构思建议。")
              }}
              className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/15 hover:bg-primary/10 hover:border-primary/30 p-2.5 transition-all text-left group"
            >
              <div className="rounded-lg bg-purple-500/10 p-1.5 group-hover:bg-purple-500/20 text-purple-400 transition-colors">
                <Wand2 className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-foreground block">续写建议</span>
                <span className="text-[9px] text-muted-foreground block truncate">启发后文创作</span>
              </div>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* 质检报告卡片 - 有诊断结果时显示 */}
      {diagnosisResult && (
        <Card className="glass-panel border-amber-500/20 bg-amber-500/5 hover:shadow-[0_0_20px_rgba(245,158,11,0.05)] transition-all duration-300 shrink-0">
          <CardHeader className="pb-1.5 pt-3 px-4 flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
              <Gauge className="h-3.5 w-3.5" />
              本章质检诊断报告
            </CardTitle>
            <button
              type="button"
              onClick={() => {
                setSelectedFixIssues(diagnosisItems.filter(i => i.autoFixable).map(i => i.type))
                setFixDialogOpen(true)
              }}
              className="text-[10px] text-amber-500 hover:text-amber-400 font-medium transition-colors"
            >
              一键优化本章
            </button>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-1 space-y-2.5">
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {diagnosisItems.filter(i => i.autoFixable).map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-1.5 rounded-lg border border-border/30 bg-card/10 p-2 text-[10px]"
                >
                  <input
                    type="checkbox"
                    checked={selectedFixIssues.includes(item.type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedFixIssues(prev => [...prev, item.type])
                      } else {
                        setSelectedFixIssues(prev => prev.filter(t => t !== item.type))
                      }
                    }}
                    className="mt-0.5 h-3 w-3 shrink-0 accent-amber-500"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-foreground truncate">{item.type}</p>
                    <p className="text-muted-foreground leading-tight mt-0.5 line-clamp-2">{item.description}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFixIssues([item.type])
                      setFixDialogOpen(true)
                    }}
                    className="shrink-0 px-2 py-0.5 rounded text-[9px] text-amber-400 hover:bg-amber-500/10 transition-colors"
                  >
                    优化
                  </button>
                </div>
              ))}
            </div>

            {diagnosisItems.filter(i => !i.autoFixable).length > 0 && (
              <details className="text-[10px] text-muted-foreground bg-muted/10 border border-border/20 rounded-lg p-2">
                <summary className="cursor-pointer hover:text-foreground font-medium select-none text-[10px]">
                  查看其他不可自动优化信息 ({diagnosisItems.filter(i => !i.autoFixable).length} 项)
                </summary>
                <div className="mt-1.5 space-y-1 border-t border-border/10 pt-1.5">
                  {diagnosisItems.filter(i => !i.autoFixable).map((item) => (
                    <p key={item.id} className="leading-relaxed text-[9px]">
                      <span className="font-semibold text-foreground">{item.type}：</span>
                      {item.description}
                    </p>
                  ))}
                </div>
              </details>
            )}
          </CardContent>
        </Card>
      )}

      {/* 根据诊断优化对话框 */}
      <DiagnosisFixDialog
        open={fixDialogOpen}
        onOpenChange={setFixDialogOpen}
        chapterContent={chapterEditorContent}
        diagnosis={diagnosisResult}
        selectedIssues={selectedFixIssues}
        projectId={projectId}
        chapterNumber={selectedChapterNumber}
        onApply={(optimizedContent) => {
          setChapterEditorContent(optimizedContent)
          setFixDialogOpen(false)
        }}
      />
    </div>
  )
}
