"use client"

import React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckCircle, Loader2, Save, Play, Ban, AlertCircle, RefreshCcw, Info, MoreVertical, Trash2, ChevronDown } from "lucide-react"
import { useProjectContext } from "../ProjectContext"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import type { Chapter } from "@/lib/types"
import { FloatingToolbar } from "./FloatingToolbar"
import { DeleteChapterDialog } from "./DeleteChapterDialog"

export function WorkbenchEditor() {
  const {
    projectId,
    chapters,
    refetchChapters,
    config,
    platform,
    generation: {
      generationTaskId, generationStopping, sseAction, isConnected, events, sseError,
      handleStopGeneration, handleRetryGeneration, startTask, enableBrainstorming, setEnableBrainstorming
    },
    workbench: {
      selectedChapterNumber,
      chapterEditorContent, setChapterEditorContent,
      chapterEditorLoading, chapterEditorSaving,
      activeChapterMeta, saveWorkbenchChapter, loadWorkbenchChapter
    }
  } = useProjectContext()

  const selectedChapterFromList = chapters?.find((c: Chapter) => c.chapter_number === selectedChapterNumber)

  // -- Word Count & Hook Score Deviation Calculations --
  const currentWordCount = chapterEditorContent?.length || activeChapterMeta?.word_count || 0
  const targetWordCount = config?.word_number || 3000
  const wordCountDeviation = targetWordCount > 0 ? Math.abs(currentWordCount - targetWordCount) / targetWordCount : 0
  const isWordCountDeviating = currentWordCount > 0 && wordCountDeviation > 0.2
  const deviationPercent = wordCountDeviation * 100
  const wordCountDiff = currentWordCount - targetWordCount

  const hookResult = platform?.hookResult
  const hasLowHookScore = hookResult && (hookResult.score || 0) < 7

  // -- Interactive Editing State --
  const [toolbarState, setToolbarState] = React.useState({ x: 0, y: 0, visible: false, startIndex: 0, endIndex: 0 })
  const [isRewriting, setIsRewriting] = React.useState(false)
  const [showReference, setShowReference] = React.useState(false)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  // -- Delete / More-menu state --
  const [moreMenuOpen, setMoreMenuOpen] = React.useState(false)
  const [deleteTarget, setDeleteTarget] = React.useState<Chapter | null>(null)
  const moreMenuRef = React.useRef<HTMLDivElement | null>(null)

  React.useEffect(() => {
    if (!moreMenuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(e.target as Node)) {
        setMoreMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [moreMenuOpen])

  const handleDeletedChapter = () => {
    setMoreMenuOpen(false)
    // After deletion the sidebar logic will handle navigation;
    // we just clear local state
    setChapterEditorContent("")
  }

  const handleMouseUp = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement
    const start = target.selectionStart
    const end = target.selectionEnd
    if (start !== end && end - start > 0) {
      setToolbarState({
        x: e.clientX,
        y: e.clientY - 20,
        visible: true,
        startIndex: start,
        endIndex: end
      })
    } else {
      setToolbarState(prev => ({ ...prev, visible: false }))
    }
  }

  const handleRewriteSubmit = async (instruction: string) => {
    if (!chapterEditorContent || toolbarState.startIndex === toolbarState.endIndex) return
    setIsRewriting(true)
    
    const contextBefore = chapterEditorContent.substring(Math.max(0, toolbarState.startIndex - 500), toolbarState.startIndex)
    const selectedText = chapterEditorContent.substring(toolbarState.startIndex, toolbarState.endIndex)
    const contextAfter = chapterEditorContent.substring(toolbarState.endIndex, Math.min(chapterEditorContent.length, toolbarState.endIndex + 500))

    try {
      const response = await fetch(api.interactive.getRewriteUrl(projectId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context_before: contextBefore,
          selected_text: selectedText,
          context_after: contextAfter,
          user_instruction: instruction
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "请求重写失败")
      }
      if (!response.body) throw new Error("没有流返回")

      const reader = response.body.getReader()
      const decoder = new TextDecoder("utf-8")
      let rewrittenText = ""
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\\n")
        buffer = lines.pop() || ""
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const dataStr = JSON.parse(line.substring(6))
              // The backend sends payload.event and payload.data, wait, backend sends {"event": "...", "data": ...}
              const payload = typeof dataStr === 'string' ? JSON.parse(dataStr) : dataStr
              
              if (payload.content) {
                 rewrittenText = payload.content
                 setChapterEditorContent(prev => {
                   return prev.substring(0, toolbarState.startIndex) + rewrittenText + prev.substring(toolbarState.endIndex)
                 })
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      }
      
      setToolbarState(prev => ({ ...prev, visible: false, endIndex: prev.startIndex + rewrittenText.length }))
      toast.success("局部重写完成！")
      
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setIsRewriting(false)
    }
  }
  // -----------------------------

  const handleGenerateWorkbenchChapter = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      const url = `/api/v1/projects/${projectId}/generate/chapter/${selectedChapterNumber}${enableBrainstorming ? "?enable_brainstorming=true" : ""}`
      startTask("chapter", url, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleFinalizeWorkbenchChapter = async () => {
    if (!chapterEditorContent.trim()) return
    await saveWorkbenchChapter()
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      startTask("finalize", `/api/v1/projects/${projectId}/generate/finalize/${selectedChapterNumber}`, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  React.useEffect(() => {
    loadWorkbenchChapter(selectedChapterNumber)
  }, [selectedChapterNumber, loadWorkbenchChapter])

  const lastPartial = events.filter((e: any) => e.type === "partial").pop()

  React.useEffect(() => {
    if ((sseAction === "chapter" || sseAction === "chapterBatch") && lastPartial?.data?.content) {
      if (lastPartial.data.step === "draft" || lastPartial.data.step === "voice_polish" || lastPartial.data.step === "quality_rewrite") {
        setChapterEditorContent(lastPartial.data.content)
      }
    }
  }, [lastPartial, sseAction, setChapterEditorContent])

  React.useEffect(() => {
    if (events.length > 0) {
      const lastEvent = events[events.length - 1]
      if (lastEvent.type === "done" && (sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize")) {
        loadWorkbenchChapter(selectedChapterNumber)
        refetchChapters()
      }
    }
  }, [events, sseAction, selectedChapterNumber, loadWorkbenchChapter, refetchChapters])

  return (
    <Card className="glass-panel border-border/40 h-full flex flex-col hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
      <CardHeader className="border-b border-border/20 pb-2 shrink-0 px-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex items-center gap-3">
            <CardTitle className="truncate text-base font-bold">
              第{selectedChapterNumber}章 {activeChapterMeta?.chapter_title || selectedChapterFromList?.chapter_title || ""}
            </CardTitle>
            <Badge
              variant={activeChapterMeta?.status === "final" ? "default" : activeChapterMeta?.status === "draft" ? "secondary" : "outline"}
              className={
                activeChapterMeta?.status === "final"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] px-1.5 py-0"
                  : activeChapterMeta?.status === "draft"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px] px-1.5 py-0"
                  : "bg-secondary text-muted-foreground text-[10px] px-1.5 py-0"
              }
            >
              {activeChapterMeta?.status === "final" ? "定稿" : activeChapterMeta?.status === "draft" ? "草稿" : "待生成"}
            </Badge>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Badge variant="outline" className="border-border bg-card/50 text-[10px] px-1.5 py-0">
              {activeChapterMeta?.word_count || chapterEditorContent.length || 0} 字
            </Badge>
            {isWordCountDeviating && (
              <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] px-1.5 py-0">
                ±{Math.round(deviationPercent)}%
              </Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowReference(!showReference)}
              className={`h-6 px-1.5 text-[10px] transition-colors ${showReference ? 'bg-secondary text-secondary-foreground border-secondary-foreground/20' : 'text-muted-foreground hover:text-foreground'}`}
              title="查看当前大纲和参考资料"
            >
              <Info className="h-3 w-3 mr-1" />
              参考资料
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 min-w-0 flex flex-col space-y-4 pt-4 pb-4">
        {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && isConnected && (
          <div className="flex items-center gap-2 rounded-xl bg-primary/10 border border-primary/20 p-3 text-sm text-primary animate-glow-pulse relative overflow-hidden shrink-0">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/20 to-transparent -translate-x-[100%] animate-[shimmer_2s_infinite]" />
            <Loader2 className="h-4 w-4 animate-spin shrink-0" />
            <span>AI 正在处理第{selectedChapterNumber}章...</span>
          </div>
        )}
        {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") &&
          events.filter((e: any) => e.type === "progress").slice(-3).map((event: any, index: number) => (
            <div key={`${event.data.step}-${index}`} className="flex items-start gap-2 rounded-xl bg-muted/40 border border-border/50 p-2.5 text-xs shrink-0">
              {event.data.status === "done" ? (
                <CheckCircle className="mt-0.5 h-3.5 w-3.5 text-emerald-400 shrink-0" />
              ) : (
                <Loader2 className="mt-0.5 h-3.5 w-3.5 animate-spin text-primary shrink-0" />
              )}
              <span>{event.data.message}</span>
            </div>
          ))}
        {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && sseError && (
          <div className="flex items-start gap-2 rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive shrink-0">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <span>{sseError || "生成失败"}</span>
              <div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleRetryGeneration} 
                  className="text-foreground hover:text-foreground/80 h-7 text-xs"
                >
                  <RefreshCcw className="w-3 h-3 mr-1.5" />
                  从断点重试
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Alerts Banner */}
        {!chapterEditorLoading && (isWordCountDeviating || hasLowHookScore) && (
          <div className="flex flex-col gap-2 rounded-xl border border-border/30 bg-secondary/10 p-3 text-xs shrink-0">
            {isWordCountDeviating && (
              <div className="flex items-start gap-2 text-amber-500">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  <strong>字数建议：</strong>当前 {wordCountDiff > 0 ? `比目标多 ${wordCountDiff} 字` : `比目标少 ${Math.abs(wordCountDiff)} 字`}（偏差 {Math.round(deviationPercent)}%）。可考虑{wordCountDiff > 0 ? '拆章或精简冗余描写' : '丰富细节或增加情节铺垫'}。
                </span>
              </div>
            )}
            {hasLowHookScore && (
              <div className="flex items-start gap-2 text-amber-500">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  <strong>开篇建议：</strong>当前首章抓力评分 {hookResult.score}/10，低于参考线 7 分。可参考右侧质检面板的改写建议进行打磨。
                </span>
              </div>
            )}
          </div>
        )}

        {chapterEditorLoading ? (
          <div className="space-y-3 py-6 flex-1 flex flex-col min-h-0 min-w-0">
            <Skeleton className="h-4 w-1/3 shrink-0" />
            <Skeleton className="h-4 w-2/3 shrink-0" />
            <Skeleton className="flex-1 w-full rounded-xl" />
          </div>
        ) : (
          <div className="flex-1 min-h-0 min-w-0 flex gap-4 relative">
            <div className="flex-1 min-w-0 h-full relative">
              <FloatingToolbar
                x={toolbarState.x}
                y={toolbarState.y}
                visible={toolbarState.visible}
                isSubmitting={isRewriting}
                onClose={() => setToolbarState(prev => ({ ...prev, visible: false }))}
                onSubmit={handleRewriteSubmit}
              />

              {/* Empty draft content warning */}
              {!chapterEditorContent && activeChapterMeta?.status === 'draft' && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 z-10 bg-background/30 pointer-events-none">
                  <div className="rounded-full bg-amber-500/10 p-3 mb-3">
                    <AlertCircle className="h-6 w-6 text-amber-400" />
                  </div>
                  <p className="text-sm font-semibold text-amber-400">草稿内容为空</p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                    该章节状态为"草稿"，但正文内容不存在。可能文件已被删除或生成过程出现异常。
                  </p>
                  <p className="text-xs text-muted-foreground mt-3">
                    请尝试重新生成，或在下方编辑器中直接编写内容后保存。
                  </p>
                </div>
              )}

              {/* Final chapter read-only indicator */}
              {activeChapterMeta?.status === 'final' && (
                <div className="absolute top-2 right-2 z-10">
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 text-[10px]">
                    <CheckCircle className="h-3 w-3" />
                    已定稿
                  </span>
                </div>
              )}

              <Textarea
                ref={textareaRef}
                value={chapterEditorContent}
                onChange={(event) => {
                  if (activeChapterMeta?.status === 'final') {
                    toast.info('该章节已定稿，如需编辑请先取消定稿。')
                    return
                  }
                  setChapterEditorContent(event.target.value)
                }}
                onMouseUp={(e) => {
                  if (activeChapterMeta?.status === 'final') return
                  handleMouseUp(e)
                }}
                onKeyUp={(e) => {
                   if (activeChapterMeta?.status === 'final') return
                   if (e.shiftKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
                     handleMouseUp(e as any)
                   }
                }}
                className={`h-full w-full resize-none font-serif text-base md:text-lg md:leading-8 leading-7 tracking-wider p-6 md:p-8 bg-background/30 border-border/80 rounded-xl transition-all overflow-y-auto ${
                  activeChapterMeta?.status === 'final'
                    ? 'focus-visible:ring-0 opacity-70 cursor-not-allowed'
                    : 'focus-visible:ring-primary/25'
                }`}
                style={{ fieldSizing: 'fixed' } as React.CSSProperties}
                placeholder={
                  activeChapterMeta?.status === 'final'
                    ? '该章节已定稿，内容为只读。'
                    : activeChapterMeta?.status === 'draft' && !chapterEditorContent
                    ? '草稿内容为空，在此编写后保存可恢复。'
                    : '在此编写章节内容... 选中任意文字可进行局部改写。'
                }
                readOnly={activeChapterMeta?.status === 'final'}
              />
            </div>

            {showReference && (
              <div className="w-[280px] shrink-0 border-l border-border/20 pl-4 overflow-y-auto hidden md:flex flex-col space-y-4 animate-in slide-in-from-right-4 duration-300">
                <div className="flex items-center justify-between pb-1 border-b border-border/20">
                  <h4 className="text-xs font-bold text-foreground">本章大纲与参考</h4>
                  <Button variant="ghost" size="icon" className="h-5 w-5 hover:bg-muted" onClick={() => setShowReference(false)}>
                    <span className="text-xs">×</span>
                  </Button>
                </div>
                
                {/* 章节大纲定位 */}
                <div className="space-y-1.5">
                  <span className="text-[10px] text-muted-foreground uppercase font-semibold">章节大纲</span>
                  <div className="bg-muted/40 border border-border/50 rounded-lg p-2.5 space-y-1 text-xs">
                    <p><strong>定位：</strong>{activeChapterMeta?.chapter_role || "未指定"}</p>
                    <p><strong>作用：</strong>{activeChapterMeta?.chapter_purpose || "未指定"}</p>
                    {activeChapterMeta?.chapter_summary && (
                      <p className="mt-1.5 leading-relaxed text-muted-foreground"><strong>推进目标：</strong>{activeChapterMeta.chapter_summary}</p>
                    )}
                  </div>
                </div>

                {/* 伏笔悬念 */}
                {activeChapterMeta?.foreshadowing && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">伏笔悬念</span>
                    <div className="bg-muted/40 border border-border/50 rounded-lg p-2.5 text-xs leading-relaxed text-muted-foreground">
                      {activeChapterMeta.foreshadowing}
                    </div>
                  </div>
                )}

                {/* 写作配置要求 */}
                <div className="space-y-1.5">
                  <span className="text-[10px] text-muted-foreground uppercase font-semibold">写作配置要求</span>
                  <div className="bg-muted/40 border border-border/50 rounded-lg p-2.5 space-y-2 text-xs">
                    {config?.topic && (
                      <p><strong>主题/金手指：</strong>{config.topic}</p>
                    )}
                    {config?.style_requirement && (
                      <p><strong>文风要求：</strong>{config.style_requirement}</p>
                    )}
                    {config?.forbidden && (
                      <p className="text-amber-500/90"><strong>避雷限制：</strong>{config.forbidden}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-2 shrink-0">
          <Button size="sm" variant="outline" onClick={async () => {
            const meta = await saveWorkbenchChapter()
            if (meta) refetchChapters()
          }} disabled={chapterEditorSaving || chapterEditorLoading}>
            {chapterEditorSaving ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
            保存
          </Button>
          <Button size="sm" onClick={handleGenerateWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping} className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white border-0 shadow-sm shadow-purple-500/20 hover:shadow transition-all duration-200">
            <Play className="h-4 w-4 mr-1.5 fill-current" />AI 生成
          </Button>
          <Button size="sm" onClick={handleFinalizeWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping || !chapterEditorContent.trim()} className="bg-emerald-600 hover:bg-emerald-700 text-white border-0 shadow-sm transition-all duration-200">
            <CheckCircle className="h-4 w-4 mr-1.5 text-emerald-100" />定稿
          </Button>
          {generationTaskId && (
            <Button size="sm" variant="destructive" onClick={handleStopGeneration} disabled={generationStopping}>
              {generationStopping ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Ban className="h-4 w-4 mr-1.5" />}
              中断
            </Button>
          )}

          {/* More actions dropdown */}
          <div className="relative ml-auto">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setMoreMenuOpen(!moreMenuOpen)}
              className="h-7 px-2 text-muted-foreground hover:text-foreground text-[11px]"
            >
              <MoreVertical className="h-3.5 w-3.5 mr-1" />
              更多
              <ChevronDown className={`h-3 w-3 ml-0.5 transition-transform ${moreMenuOpen ? 'rotate-180' : ''}`} />
            </Button>

            {moreMenuOpen && (
              <div
                ref={moreMenuRef}
                className="absolute right-0 bottom-full mb-1 z-50 min-w-[140px] rounded-lg border border-border/50 bg-popover backdrop-blur-xl shadow-xl py-1 animate-in fade-in zoom-in-95 duration-150"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 transition-colors"
                  onClick={() => {
                    const target = chapters?.find((c: Chapter) => c.chapter_number === selectedChapterNumber) || null
                    setDeleteTarget(target)
                    setMoreMenuOpen(false)
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  删除草稿
                </button>
              </div>
            )}
          </div>

          {/* Brainstorm toggle */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-muted-foreground select-none">脑暴</span>
            <button
              type="button"
              role="switch"
              aria-checked={enableBrainstorming}
              disabled={isConnected || Boolean(generationTaskId) || generationStopping}
              onClick={() => setEnableBrainstorming(!enableBrainstorming)}
              className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 ${
                enableBrainstorming ? "bg-primary" : "bg-muted-foreground/30"
              }`}
            >
              <span
                className={`pointer-events-none block h-3 w-3 rounded-full bg-background shadow-md ring-0 transition-transform duration-300 ${
                  enableBrainstorming ? "translate-x-3.5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>
        </div>
      </CardContent>

      {/* Delete confirmation dialog */}
      <DeleteChapterDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        chapter={deleteTarget}
        projectId={projectId}
        onDeleted={handleDeletedChapter}
      />
    </Card>
  )
}
