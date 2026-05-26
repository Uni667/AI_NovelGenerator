"use client"

import React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckCircle, Loader2, Save, Play, Ban, AlertCircle, RefreshCcw } from "lucide-react"
import { useProjectContext } from "../ProjectContext"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import type { Chapter } from "@/lib/types"
import { FloatingToolbar } from "./FloatingToolbar"

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

  const hookResult = platform?.hookResult
  const hasLowHookScore = hookResult && (hookResult.score || 0) < 7

  // -- Interactive Editing State --
  const [toolbarState, setToolbarState] = React.useState({ x: 0, y: 0, visible: false, startIndex: 0, endIndex: 0 })
  const [isRewriting, setIsRewriting] = React.useState(false)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

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
      <CardHeader className="border-b border-border/30 pb-4 shrink-0">
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
            {isWordCountDeviating && (
              <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                字数偏离 {Math.round(deviationPercent)}%
              </Badge>
            )}
            {hasLowHookScore && (
              <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20 animate-pulse flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5 text-destructive shrink-0" />
                开篇抓力低 ({hookResult.score}分)
              </Badge>
            )}
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
      <CardContent className="flex-1 min-h-0 flex flex-col space-y-4 pt-4 pb-4">
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
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  <strong>字数偏离警告：</strong>当前章节字数已达 {currentWordCount} 字，偏离了目标值 ({targetWordCount} 字) {Math.round(deviationPercent)}%。可能存在剧情拖沓灌水或细节不够饱满，请注意把控节奏。
                </span>
              </div>
            )}
            {hasLowHookScore && (
              <div className="flex items-start gap-2 text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  <strong>开篇抓力预警：</strong>当前章节作为开篇，首章抓力评分仅为 {hookResult.score}/10分，低于安全基准线（7分）。强烈建议参考右侧状态面板的“平台辅助质检”改写意见，进行细节打磨。
                </span>
              </div>
            )}
          </div>
        )}

        {chapterEditorLoading ? (
          <div className="space-y-3 py-6 flex-1 flex flex-col min-h-0">
            <Skeleton className="h-4 w-1/3 shrink-0" />
            <Skeleton className="h-4 w-2/3 shrink-0" />
            <Skeleton className="flex-1 w-full rounded-xl" />
          </div>
        ) : (
          <div className="flex-1 min-h-0 relative">
            <FloatingToolbar
              x={toolbarState.x}
              y={toolbarState.y}
              visible={toolbarState.visible}
              isSubmitting={isRewriting}
              onClose={() => setToolbarState(prev => ({ ...prev, visible: false }))}
              onSubmit={handleRewriteSubmit}
            />
            <Textarea
              ref={textareaRef}
              value={chapterEditorContent}
              onChange={(event) => setChapterEditorContent(event.target.value)}
              onMouseUp={handleMouseUp}
              onKeyUp={(e) => {
                 // Also handle keyboard selection
                 if (e.shiftKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
                   handleMouseUp(e as any)
                 }
              }}
              className="h-full w-full resize-none font-serif text-base md:text-lg leading-8 tracking-wider p-4 bg-background/30 focus-visible:ring-primary/25 border-border/80 rounded-xl transition-all"
              placeholder="在这里生成、编辑、保存章节草稿... 选中任意文字即可进行局部指令重写。"
            />
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3 pt-2 shrink-0">
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
          <div className="flex items-center space-x-2 ml-auto">
            <button
              type="button"
              role="switch"
              aria-checked={enableBrainstorming}
              disabled={isConnected || Boolean(generationTaskId) || generationStopping}
              onClick={() => setEnableBrainstorming(!enableBrainstorming)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 ${
                enableBrainstorming ? "bg-primary" : "bg-muted-foreground/30"
              }`}
            >
              <span
                className={`pointer-events-none block h-4 w-4 rounded-full bg-background shadow-md ring-0 transition-transform duration-300 ${
                  enableBrainstorming ? "translate-x-4" : "translate-x-0.5"
                }`}
              />
            </button>
            <span className="text-xs text-muted-foreground select-none cursor-pointer" onClick={() => {
              if (!isConnected && !generationTaskId && !generationStopping) {
                setEnableBrainstorming(!enableBrainstorming)
              }
            }}>
              开启多智能体脑暴
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
