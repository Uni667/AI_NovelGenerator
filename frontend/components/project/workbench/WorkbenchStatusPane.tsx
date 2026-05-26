"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { Loader2, Target, Eye, FileEdit, Gauge, AlertCircle, Ban, CheckCircle, RefreshCcw, Sparkles, Info } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { useProjectContext } from "../ProjectContext"
import type { Chapter } from "@/lib/types"

export function WorkbenchStatusPane() {
  const {
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
    },
    platform: {
      platformLoading, chapterTitles, hookResult, chapterHookResult, diagnosisResult,
      handleGenSelectedChapterTitle, handleWorkbenchOpeningHook,
      handleWorkbenchEndingHook, handleDiagnoseChapter
    }
  } = useProjectContext()

  const [accordionValue, setAccordionValue] = useState<string[]>(["basic", "structure", "foreshadow", "wordcount", "quality"])

  const currentWordCount = chapterEditorContent?.length || activeChapterMeta?.word_count || 0
  const targetWordCount = config?.word_number || 3000
  const wordCountDeviation = targetWordCount > 0 ? Math.abs(currentWordCount - targetWordCount) / targetWordCount : 0
  const isWordCountDeviating = currentWordCount > 0 && wordCountDeviation > 0.2
  const deviationPercent = wordCountDeviation * 100
  const wordCountDiff = currentWordCount - targetWordCount

  const totalWords = chapters?.reduce((acc: number, cur: Chapter) => acc + (cur.word_count || 0), 0) || 0

  const isChapterAction = sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize"
  const progressEvents = events.filter((e: any) => e.type === "progress")

  return (
    <div className="space-y-6 h-full overflow-y-auto pr-1">
      {/* 生成进度卡片 - 有活跃任务时显示 */}
      {(isConnected || generationTaskId) && (
        <Card className="glass-panel border-primary/30 bg-primary/5 shadow-lg shadow-primary/5 animate-glow-pulse">
          <CardHeader className="pb-2 border-b border-primary/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
                <Sparkles className="h-4 w-4" />
                生成进度
              </CardTitle>
              <Badge
                variant={generationStopping ? "secondary" : "outline"}
                className={
                  generationStopping
                    ? "bg-secondary text-muted-foreground text-[10px]"
                    : isConnected
                    ? "bg-primary/10 text-primary border-primary/20 text-[10px]"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]"
                }
              >
                {generationStopping ? "停止中" : isConnected ? "进行中" : "后台继续中"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-3 text-xs">
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
              <Progress value={generationProgress} className="w-full h-1.5" />
            </div>

            {/* Recent progress events */}
            {progressEvents.length > 0 && (
              <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
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
                className="w-full h-7 text-[10px]"
              >
                {generationStopping ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Ban className="h-3 w-3 mr-1" />}
                中断生成
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="glass-panel border-border/40">
        <CardHeader className="pb-2 px-4">
          <CardTitle className="text-xs font-bold text-muted-foreground">章节属性与质检</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-3">
          <Accordion type="multiple" value={accordionValue} onValueChange={setAccordionValue} className="w-full">
            {/* 基础信息 */}
            <AccordionItem value="basic">
              <AccordionTrigger className="py-1.5 text-xs font-semibold">基础信息</AccordionTrigger>
              <AccordionContent className="text-xs">
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground shrink-0">章节定位：</span>
                    <span className="font-medium text-right">{activeChapterMeta?.chapter_role || "-"}</span>
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground shrink-0">核心作用：</span>
                    <span className="font-medium text-right">{activeChapterMeta?.chapter_purpose || "-"}</span>
                  </div>
                  <Separator className="bg-border/20 my-1" />
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>项目总字数：</span>
                    <span className="font-semibold text-foreground">{totalWords} 字</span>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* 剧情结构 */}
            <AccordionItem value="structure">
              <AccordionTrigger className="py-1.5 text-xs font-semibold">剧情结构</AccordionTrigger>
              <AccordionContent className="text-xs">
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground shrink-0">核心作用：</span>
                    <span className="font-medium text-right">{activeChapterMeta?.chapter_purpose || "-"}</span>
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground shrink-0">认知颠覆：</span>
                    <span className="font-medium text-right">{activeChapterMeta?.plot_twist_level || "-"}</span>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* 伏笔悬念 */}
            <AccordionItem value="foreshadow">
              <AccordionTrigger className="py-1.5 text-xs font-semibold">伏笔悬念</AccordionTrigger>
              <AccordionContent className="text-xs">
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground shrink-0">悬念密度：</span>
                    <span className="font-medium text-right">{activeChapterMeta?.suspense_level || "-"}</span>
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground shrink-0">伏笔操作：</span>
                    <span className="font-medium text-right">{activeChapterMeta?.foreshadowing || "-"}</span>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* 字数节奏 */}
            <AccordionItem value="wordcount">
              <AccordionTrigger className="py-1.5 text-xs font-semibold">字数节奏</AccordionTrigger>
              <AccordionContent className="text-xs">
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">本章：</span>
                    <span className="font-semibold">{currentWordCount} 字</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">目标：</span>
                    <span className="font-semibold">{targetWordCount} 字</span>
                  </div>
                  {isWordCountDeviating && (
                    <div className="flex items-start gap-1.5 rounded-lg border border-amber-500/20 bg-amber-500/5 p-2 text-[10px] mt-1">
                      <Info className="h-3 w-3 shrink-0 text-amber-400 mt-0.5" />
                      <div className="text-amber-300">
                        <p className="font-medium">字数建议</p>
                        <p className="text-muted-foreground mt-0.5 leading-relaxed">
                          {wordCountDiff > 0
                            ? `当前比目标多 ${wordCountDiff} 字（+${Math.round(deviationPercent)}%）。可考虑拆章、精简冗余描写，或调整目标字数。`
                            : `当前比目标少 ${Math.abs(wordCountDiff)} 字（-${Math.round(deviationPercent)}%）。可适当丰富细节描写或增加情节铺垫。`
                          }
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* 平台质检 */}
            <AccordionItem value="quality">
              <AccordionTrigger className="py-1.5 text-xs font-semibold">平台质检</AccordionTrigger>
              <AccordionContent className="text-xs">
                <div className="space-y-2 pt-1">
                  <div className="flex flex-col gap-1.5">
                    <Button size="sm" className="w-full justify-start text-[11px] h-7 bg-card/30 border-border/80" variant="outline" onClick={() => handleWorkbenchOpeningHook(1)} disabled={platformLoading === "workbenchOpening"}>
                      {platformLoading === "workbenchOpening" ? <Loader2 className="h-3 w-3 mr-1.5 animate-spin" /> : <Target className="h-3 w-3 mr-1.5 text-indigo-400" />}
                      检测开篇抓力
                    </Button>
                    <Button size="sm" className="w-full justify-start text-[11px] h-7 bg-card/30 border-border/80" variant="outline" onClick={() => handleWorkbenchEndingHook(selectedChapterNumber)} disabled={platformLoading === "workbenchEnding"}>
                      {platformLoading === "workbenchEnding" ? <Loader2 className="h-3 w-3 mr-1.5 animate-spin" /> : <Eye className="h-3 w-3 mr-1.5 text-emerald-400" />}
                      检测结尾钩子
                    </Button>
                    <Button size="sm" className="w-full justify-start text-[11px] h-7 bg-card/30 border-border/80" variant="outline" onClick={() => handleGenSelectedChapterTitle(selectedChapterNumber)} disabled={platformLoading === "workbenchTitle"}>
                      {platformLoading === "workbenchTitle" ? <Loader2 className="h-3 w-3 mr-1.5 animate-spin" /> : <FileEdit className="h-3 w-3 mr-1.5 text-blue-400" />}
                      生成章节标题
                    </Button>
                  </div>

                  {chapterTitles.length > 0 && (
                    <div className="space-y-1 rounded-lg border border-border/50 bg-secondary/20 p-2">
                      <p className="text-[9px] text-muted-foreground uppercase font-semibold">标题候选</p>
                      {chapterTitles.map((title: string, index: number) => <p key={index} className="text-[11px] leading-tight font-medium">「{title}」</p>)}
                    </div>
                  )}
                  {hookResult && (
                    <div className="space-y-1.5 rounded-lg border border-border/50 p-2 text-[11px] bg-card/10">
                      {(hookResult.score || 0) < 7 && (
                        <div className="flex items-start gap-1.5 rounded border border-amber-500/20 bg-amber-500/5 p-1.5 text-[10px] text-amber-300 mb-1">
                          <Info className="h-3 w-3 shrink-0 mt-0.5" />
                          <div>
                            <p className="font-medium">开篇抓力建议</p>
                            <p className="text-muted-foreground mt-0.5">当前评分低于 7 分的参考线，可参考右侧建议进行优化。</p>
                          </div>
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">开篇评分</span>
                        <Badge variant={(hookResult.score || 0) >= 7 ? "default" : "secondary"} className={(hookResult.score || 0) >= 7 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[9px] px-1.5" : "bg-amber-500/10 text-amber-400 border-amber-500/20 text-[9px] px-1.5"}>{hookResult.score}/10</Badge>
                      </div>
                      {hookResult.rewrite_suggestion && <p className="text-muted-foreground leading-relaxed mt-1 text-[10px]">{hookResult.rewrite_suggestion}</p>}
                    </div>
                  )}
                  {chapterHookResult && (
                    <div className="space-y-1.5 rounded-lg border border-border/50 p-2 text-[11px] bg-card/10">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">结尾钩子</span>
                        <Badge variant={chapterHookResult.has_hook ? "default" : "secondary"} className={chapterHookResult.has_hook ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[9px] px-1.5" : "bg-amber-500/10 text-amber-400 border-amber-500/20 text-[9px] px-1.5"}>
                          {chapterHookResult.has_hook ? "合格" : "需加强"}
                        </Badge>
                      </div>
                      {chapterHookResult.suggestion && <p className="text-muted-foreground leading-relaxed mt-1 text-[10px]">{chapterHookResult.suggestion}</p>}
                    </div>
                  )}

                  <Separator className="bg-border/20" />
                  <Button size="sm" className="w-full justify-start text-[11px] h-7 bg-card/30 border-border/80" variant="outline" onClick={() => handleDiagnoseChapter(selectedChapterNumber)} disabled={platformLoading === "diagnosis"}>
                    {platformLoading === "diagnosis" ? <Loader2 className="h-3 w-3 mr-1.5 animate-spin" /> : <Gauge className="h-3 w-3 mr-1.5 text-amber-400" />}
                    诊断本章文风
                  </Button>

                  {diagnosisResult && (
                    <div className="space-y-1.5 rounded-lg border border-border/50 bg-secondary/20 p-2 text-[11px] max-h-48 overflow-auto">
                      <p className="text-[9px] text-muted-foreground uppercase font-semibold border-b border-border/20 pb-1">文风诊断</p>
                      {diagnosisResult.split("\n").map((line: string, index: number) => {
                        const isHeader = line.startsWith("【")
                        if (isHeader) {
                          return <p key={index} className="font-bold text-[11px] mt-1.5 mb-0.5 text-primary">{line}</p>
                        }
                        if (line.trim()) {
                          return <p key={index} className="leading-relaxed text-muted-foreground text-[10px]">{line}</p>
                        }
                        return <div key={index} className="h-0.5" />
                      })}
                    </div>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>
    </div>
  )
}
