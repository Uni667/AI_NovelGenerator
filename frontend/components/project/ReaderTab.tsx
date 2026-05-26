"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, MessageSquare, Target, Eye, RefreshCw, AlertTriangle, CheckCircle2, Flame, ThumbsUp } from "lucide-react"
import { PLATFORM_CONFIG } from "@/lib/types"
import { useProjectContext } from "./ProjectContext"
import { useState } from "react"
import type { Chapter } from "@/lib/types"

export function ReaderTab() {
  const { config, chapters, platform } = useProjectContext()
  const {
    hookResult, chapterHookResult, batchHookResult, platformLoading,
    handleWorkbenchOpeningHook, handleWorkbenchEndingHook, handleBatchHookCheck
  } = platform

  const [readerChapterNum, setReaderChapterNum] = useState(1)

  const completedChapters = chapters?.filter((c: Chapter) => c.status === "final").length || 0
  const draftChapters = chapters?.filter((c: Chapter) => c.status === "draft").length || 0
  const totalWords = chapters?.reduce((acc: number, cur: Chapter) => acc + (cur.word_count || 0), 0) || 0

  const handleReaderOpeningCheck = () => handleWorkbenchOpeningHook(readerChapterNum)
  const handleReaderEndingCheck = () => handleWorkbenchEndingHook(readerChapterNum)

  const readerScore = typeof hookResult?.score === "number" ? hookResult.score : null
  const readerRiskLabel =
    readerScore === null
      ? "待评估"
      : readerScore >= 8
      ? "低流失风险"
      : readerScore >= 6
      ? "中等风险"
      : "高流失风险"
  const readerRiskVariant =
    readerScore === null
      ? "outline"
      : readerScore >= 8
      ? "default"
      : readerScore >= 6
      ? "secondary"
      : "destructive"

  const totalChaptersCount = config?.num_chapters || chapters?.length || 0

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 shadow-xl">
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-xl font-bold tracking-tight">
                <MessageSquare className="h-5 w-5 text-primary animate-pulse" />
                读者反馈 & 追读预测
              </CardTitle>
              <CardDescription>使用大模型模拟不同平台读者视角，诊断正文钩子和流失风险</CardDescription>
            </div>
            <div className="flex flex-wrap items-end gap-3 bg-secondary/10 p-2 rounded-xl border border-border/20">
              <div className="flex items-center gap-2">
                <Label className="text-xs font-semibold text-muted-foreground whitespace-nowrap">检测章节</Label>
                <Input
                  type="number"
                  min={1}
                  max={totalChaptersCount || undefined}
                  className="w-20 h-8 font-semibold text-center hover:border-primary/20"
                  value={readerChapterNum}
                  onChange={(event) => setReaderChapterNum(Math.max(1, Number(event.target.value) || 1))}
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs hover:bg-accent/40"
                onClick={handleReaderOpeningCheck}
                disabled={platformLoading === "workbenchOpening"}
              >
                {platformLoading === "workbenchOpening" ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Target className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
                )}
                开篇吸引力
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs hover:bg-accent/40"
                onClick={handleReaderEndingCheck}
                disabled={platformLoading === "workbenchEnding"}
              >
                {platformLoading === "workbenchEnding" ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Eye className="h-3.5 w-3.5 mr-1.5 text-blue-400" />
                )}
                结尾钩子
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs hover:bg-accent/40"
                onClick={handleBatchHookCheck}
                disabled={platformLoading === "batch"}
              >
                {platformLoading === "batch" ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5 text-purple-400" />
                )}
                全书结尾钩子
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* 读者指标面板 */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* 1. 首屏吸引力卡片 */}
        <Card className="glass-card border-border/40 hover:border-primary/20 transition-all duration-300">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-bold flex items-center gap-1.5">
              <Flame className="h-4.5 w-4.5 text-orange-400 animate-bounce" />
              首屏吸引力
            </CardTitle>
            <CardDescription>第 {readerChapterNum} 章前200字首屏抓人力评估</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">流失风险预测</span>
              <Badge
                variant={readerRiskVariant}
                className={
                  readerRiskVariant === "default"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : readerRiskVariant === "secondary"
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    : readerRiskVariant === "destructive"
                    ? "bg-destructive/10 text-destructive border-destructive/20 animate-pulse"
                    : ""
                }
              >
                {readerRiskLabel}
              </Badge>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-5xl font-extrabold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                {readerScore ?? "-"}
              </span>
              <span className="text-sm font-semibold text-muted-foreground">/ 10 分</span>
            </div>
            {hookResult?.hook_strength && (
              <Badge variant="outline" className="border-border bg-background/50 font-medium">
                强度级别: {hookResult.hook_strength}
              </Badge>
            )}

            {hookResult?.issues && hookResult.issues.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border/20">
                <p className="text-xs font-bold text-destructive/80 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> 诊断发现的问题：
                </p>
                <div className="space-y-1 text-xs text-muted-foreground leading-relaxed pl-1.5">
                  {hookResult.issues.map((issue: string, index: number) => (
                    <p key={index} className="flex items-start gap-1">
                      <span className="text-muted-foreground/50 select-none">•</span>
                      <span>{issue}</span>
                    </p>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 2. 结尾追读卡片 */}
        <Card className="glass-card border-border/40 hover:border-primary/20 transition-all duration-300">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-bold flex items-center gap-1.5">
              <ThumbsUp className="h-4.5 w-4.5 text-indigo-400" />
              结尾追读动力
            </CardTitle>
            <CardDescription>第 {readerChapterNum} 章结尾钩子及伏笔设置评估</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">钩子状态</span>
              <Badge
                variant={chapterHookResult?.has_hook ? "default" : "outline"}
                className={
                  chapterHookResult?.has_hook
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : "bg-secondary text-muted-foreground"
                }
              >
                {chapterHookResult ? (chapterHookResult.has_hook ? "有钩子" : "需加强") : "待评估"}
              </Badge>
            </div>
            {chapterHookResult?.hook_type && (
              <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/25 font-semibold text-xs">
                {chapterHookResult.hook_type}
              </Badge>
            )}
            {chapterHookResult?.hook_description && (
              <p className="text-xs text-muted-foreground leading-relaxed border-t border-border/20 pt-3">
                <span className="font-semibold text-foreground/90 block mb-1">结尾钩子描述:</span>
                {chapterHookResult.hook_description}
              </p>
            )}
            {chapterHookResult?.suggestion && (
              <p className="text-xs text-muted-foreground leading-relaxed bg-muted/10 border border-border/25 rounded-lg p-2.5">
                <span className="font-semibold text-foreground/90 block mb-1 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> 优化建议:
                </span>
                {chapterHookResult.suggestion}
              </p>
            )}
          </CardContent>
        </Card>

        {/* 3. 平台信号卡片 */}
        <Card className="glass-card border-border/40 hover:border-primary/20 transition-all duration-300">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-bold flex items-center gap-1.5">
              <span>{PLATFORM_CONFIG[config?.platform]?.icon || "📖"}</span>
              <span>{PLATFORM_CONFIG[config?.platform]?.label || "平台"} 推荐位数据</span>
            </CardTitle>
            <CardDescription>基于目标平台算法的综合库存及连续性指标</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3.5">
              {[
                { label: "已定稿章节", val: `${completedChapters} / ${totalChaptersCount}` },
                { label: "草稿库存", val: `${draftChapters} 章` },
                { label: "累计已写字数", val: `${totalWords.toLocaleString()} 字` },
              ].map((item, idx) => (
                <div key={idx} className="flex items-center justify-between border-b border-border/25 pb-2 text-sm last:border-0 last:pb-0">
                  <span className="text-muted-foreground/80 font-medium">{item.label}</span>
                  <span className="font-bold text-foreground">{item.val}</span>
                </div>
              ))}
            </div>
            {config?.category && (
              <div className="rounded-xl border border-border/40 bg-muted/15 p-3 text-xs text-muted-foreground leading-relaxed mt-4">
                <span className="font-semibold text-foreground/90 block mb-1">定位与流派：</span>
                项目已设定为 {config.category} · {config.genre || "无子流派"}，大模型会在评估读者吸引力时，引入该类读者的核心爽点倾向进行对齐。
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 改写建议详细面板 */}
      {hookResult?.rewrite_suggestion && (
        <Card className="glass-panel border-border/40 shadow-xl">
          <CardHeader className="pb-3 border-b border-border/30">
            <CardTitle className="text-base font-bold flex items-center gap-1.5">
              <CheckCircle2 className="h-4.5 w-4.5 text-emerald-400" />
              开篇改写润色建议
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <p className="text-sm leading-relaxed text-muted-foreground">{hookResult.rewrite_suggestion}</p>
            {hookResult.rewritten_opening && (
              <div className="rounded-xl border border-border/40 bg-muted/10 p-4">
                <p className="text-xs text-muted-foreground/90 font-bold mb-2 uppercase tracking-wide">AI 改写示范（供参考）：</p>
                <p className="text-sm font-serif leading-8 text-foreground/90 whitespace-pre-wrap pl-1">{hookResult.rewritten_opening}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 全书结尾钩子批量结果 */}
      {batchHookResult.length > 0 && (
        <Card className="glass-panel border-border/40 shadow-xl">
          <CardHeader className="pb-3 border-b border-border/30">
            <CardTitle className="text-base font-bold">全书章节结尾钩子台账 ({batchHookResult.length} 章)</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ScrollArea className="h-72 pr-2">
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {batchHookResult.map((result: any) => (
                  <div
                    key={result.chapter_number}
                    className="rounded-xl border border-border/40 bg-card/15 p-3.5 space-y-2 hover:border-primary/20 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs text-muted-foreground font-semibold">第 {result.chapter_number} 章</span>
                      <Badge
                        variant={result.has_hook ? "default" : "destructive"}
                        className={
                          result.has_hook
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px]"
                            : "bg-destructive/10 text-destructive border-destructive/20 text-[10px]"
                        }
                      >
                        {result.has_hook ? "有钩子" : "缺钩子"}
                      </Badge>
                    </div>
                    {result.hook_type && (
                      <p className="text-[11px] text-primary/95 font-bold uppercase tracking-wider">{result.hook_type}</p>
                    )}
                    {result.suggestion && (
                      <p className="text-[11px] text-muted-foreground/90 leading-relaxed bg-muted/5 p-2 rounded-lg border border-border/25">
                        {result.suggestion}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
