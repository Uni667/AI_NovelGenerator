"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Progress } from "@/components/ui/progress"
import { Play, CheckCircle, Loader2, Ban, AlertCircle, RefreshCcw, Sparkles, BookOpen, ArrowRight } from "lucide-react"
import { useProjectContext } from "./ProjectContext"
import { useState } from "react"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function GenerationTab() {
  const { projectId, generation, workbench, setActiveTab } = useProjectContext()
  const {
    generationTaskId, generationTaskLabel, generationStopping, generationRecovering,
    isConnected, events, hasError, sseError, handleStopGeneration, handleRetryGeneration, generationStepMeta,
    generationProgress, startTask, enableBrainstorming, setEnableBrainstorming,
    batchChapterIndex, batchTotalChapters, sseAction
  } = generation

  const { selectedChapterNumber } = workbench
  const [quickChapterNum, setQuickChapterNum] = useState(selectedChapterNumber)

  const lastPartial = events.filter((e: any) => e.type === "partial").pop()

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40">
        <CardHeader className="border-b border-border/30 pb-4">
          <CardTitle className="text-lg font-bold">AI 生成进度</CardTitle>
          <CardDescription>实时显示模型输出及工作流流式状态</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 pt-5">
          {(generationTaskId || generationTaskLabel) && (
            <div className="rounded-xl border border-border/50 bg-secondary/20 p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-sm truncate">{generationTaskLabel || "当前生成任务"}</p>
                  {sseAction === "chapterBatch" && batchChapterIndex > 0 && (
                    <p className="text-xs text-primary font-mono font-semibold mt-0.5">
                      第 {batchChapterIndex} / {batchTotalChapters} 章
                    </p>
                  )}
                  <p className="text-[10px] text-muted-foreground truncate mt-1">
                    任务 ID: <span className="font-mono">{generationTaskId || "待分配"}</span>
                  </p>
                </div>
                <Badge
                  variant={generationStopping ? "secondary" : "outline"}
                  className={
                    generationStopping
                      ? "bg-secondary text-muted-foreground"
                      : isConnected
                      ? "bg-primary/10 text-primary border-primary/20 animate-glow-pulse"
                      : generationRecovering
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      : "bg-muted text-muted-foreground"
                  }
                >
                  {generationStopping ? "停止中" : isConnected ? "进行中" : generationRecovering ? "后台继续中" : "待完成"}
                </Badge>
              </div>

              {/* Progress bar section */}
              {(isConnected || generationTaskId) && (
                <div className="space-y-1.5 py-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-muted-foreground">估计总进度</span>
                    <span className="font-mono font-bold text-primary">{generationProgress}%</span>
                  </div>
                  <Progress value={generationProgress} className="w-full text-xs" />
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-1">
                <Button
                  variant="destructive"
                  onClick={handleStopGeneration}
                  disabled={!generationTaskId || generationStopping}
                  className="h-8 text-xs px-3"
                >
                  {generationStopping ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Ban className="h-3.5 w-3.5 mr-1.5" />}
                  中断生成
                </Button>
              </div>
            </div>
          )}

          {events.length === 0 && !isConnected && (
            <div className="text-center py-10 text-muted-foreground border border-dashed border-border/60 rounded-xl bg-card/10 space-y-6">
              <div>
                <Play className="h-10 w-10 mx-auto mb-2 opacity-30 text-primary" />
                <p className="text-sm font-medium">无运行中的任务</p>
                <p className="text-xs text-muted-foreground mt-1">选择一个方式开始生成</p>
              </div>

              {/* Quick single chapter generate */}
              <div className="mx-auto max-w-xs space-y-3 px-4">
                <div className="rounded-xl border border-border/40 bg-background/50 p-3 space-y-2.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <Sparkles className="h-3.5 w-3.5 text-violet-400" />
                    快速生成单章
                  </div>
                  <div className="flex items-center gap-2">
                    <Label className="text-[10px] text-muted-foreground shrink-0">章节号</Label>
                    <Input
                      type="number"
                      min={1}
                      value={quickChapterNum}
                      onChange={(e) => setQuickChapterNum(Math.max(1, Number(e.target.value) || 1))}
                      className="h-7 text-xs w-20 bg-background/60 border-border/60 rounded-lg"
                    />
                    <Button
                      size="sm"
                      onClick={() => {
                        const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
                        const url = `/api/v1/projects/${projectId}/generate/chapter/${quickChapterNum}${enableBrainstorming ? "?enable_brainstorming=true" : ""}`
                        startTask("chapter", url, taskId)
                        toast.success(`已开始生成第 ${quickChapterNum} 章`)
                      }}
                      disabled={isConnected || Boolean(generationTaskId) || generationStopping}
                      className="h-7 text-xs bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white rounded-lg"
                    >
                      生成
                    </Button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setActiveTab("workbench")}
                    className="flex-1 h-8 text-xs rounded-lg"
                  >
                    <BookOpen className="h-3.5 w-3.5 mr-1.5 text-emerald-400" />
                    前往章节工作台
                    <ArrowRight className="h-3 w-3 ml-1 opacity-50" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {isConnected && (
            <div className="flex items-center gap-2 text-sm text-primary font-semibold">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>AI 正在生成中...</span>
            </div>
          )}

          {!isConnected && generationRecovering && generationTaskId && (
            <div className="flex items-center gap-2 text-sm text-amber-400 font-semibold bg-amber-500/5 border border-amber-500/10 rounded-xl p-3">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              <span>实时连接已断开，任务仍在后台继续，正在查询状态...</span>
            </div>
          )}

          <div className="space-y-2">
            {events
              .filter((e: any) => e.type === "progress")
              .map((e: any, i: number) => {
                const meta = generationStepMeta(e.data?.step)
                return (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3.5 rounded-xl border border-border/50 bg-card/30 hover:bg-card/45 transition-colors duration-150"
                  >
                    {e.data.status === "done" ? (
                      <CheckCircle className="h-5 w-5 text-emerald-400 mt-0.5 shrink-0" />
                    ) : (
                      <Loader2 className="h-5 w-5 animate-spin text-primary mt-0.5 shrink-0" />
                    )}
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-sm">{e.data.message}</p>
                        <Badge variant="outline" className="text-[10px] bg-secondary/80 py-0.5 border-border">
                          {meta.label}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{meta.description}</p>
                      <p className="text-[10px] text-muted-foreground/60 font-mono">内部步骤: {e.data.step}</p>
                    </div>
                  </div>
                )
              })}
          </div>

          {hasError && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm leading-relaxed">
              <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
              <div className="space-y-3 flex-1">
                <div>
                  <p className="font-semibold">生成过程中出现错误</p>
                  <p className="text-xs opacity-90">{sseError || "未知错误，请检查网络或模型配额"}</p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleRetryGeneration} 
                  className="text-foreground hover:text-foreground/80 h-8"
                >
                  <RefreshCcw className="w-3.5 h-3.5 mr-1.5" />
                  从断点重试
                </Button>
              </div>
            </div>
          )}

          {lastPartial && (
            <div className="p-4 rounded-xl border border-border/70 bg-background/50 space-y-2.5">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">实时生成文本预览：</p>
              <ScrollArea className="h-96 pr-2">
                <pre className="text-sm whitespace-pre-wrap font-sans leading-7 text-foreground/90 pl-1">{lastPartial.data.content}</pre>
              </ScrollArea>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
