"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Progress } from "@/components/ui/progress"
import { Play, CheckCircle, Loader2, Ban, AlertCircle } from "lucide-react"
import { useProjectContext } from "./ProjectContext"

export function GenerationTab() {
  const { generation } = useProjectContext()
  const {
    generationTaskId, generationTaskLabel, generationStopping, generationRecovering,
    isConnected, events, hasError, sseError, handleStopGeneration, generationStepMeta,
    generationProgress
  } = generation

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
            <div className="text-center py-12 text-muted-foreground border border-dashed border-border/60 rounded-xl bg-card/10">
              <Play className="h-12 w-12 mx-auto mb-3 opacity-30 text-primary" />
              <p className="text-sm font-medium">无运行中的任务</p>
              <p className="text-xs text-muted-foreground mt-1">点击「概览」或「工作台」中的生成按钮开始</p>
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
              <div className="space-y-1">
                <p className="font-semibold">生成过程中出现错误</p>
                <p className="text-xs opacity-90">{sseError || "未知错误，请检查网络或模型配额"}</p>
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
