"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Loader2, Wand2, BookMarked, FileEdit, Target, Tag, RefreshCw } from "lucide-react"
import { PLATFORM_CONFIG } from "@/lib/types"
import { useProjectContext } from "./ProjectContext"

export function PlatformToolsTab() {
  const { config, platform } = useProjectContext()
  const {
    titles, blurbs, hookResult, batchHookResult, tagsResult,
    chapterTitles, platformLoading, hookChapterNum, setHookChapterNum,
    handleGenTitles, handleGenBlurb, handleWorkbenchOpeningHook,
    handleBatchHookCheck, handleGenTags, handleGenSelectedChapterTitle
  } = platform

  const platformMeta = PLATFORM_CONFIG[config?.platform || "tomato"]

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 shadow-xl">
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-xl font-bold tracking-tight">
                <span>{platformMeta?.icon || "📖"}</span>
                <span>{platformMeta?.label || "平台"} 运营工具箱</span>
              </CardTitle>
              <CardDescription>
                针对 {platformMeta?.label || "平台"} 算法对齐特征，一键生成爆款标题、简介、标签及钩子检测
              </CardDescription>
            </div>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-xs px-3 py-1 font-semibold uppercase tracking-wider">
              算法规则已加载
            </Badge>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* 1. 书名生成 */}
        <Card className="glass-card border-border/40 hover:border-primary/10 transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold">
              <BookMarked className="h-5 w-5 text-indigo-400" />
              AI 爆款书名生成
            </CardTitle>
            <CardDescription>
              按平台最新规则公式（身份反转+冲突 / 悬念+强关键词 / 情绪承诺）生成爆款书名候选
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleGenTitles}
              disabled={platformLoading === "titles"}
              className="w-full shadow-md shadow-primary/15"
            >
              {platformLoading === "titles" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4 mr-2" />
              )}
              生成书名候选
            </Button>
            {titles.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border/20">
                {titles.map((t, i) => (
                  <div key={i} className="p-3.5 rounded-xl border border-border/40 bg-card/25 text-sm flex items-start gap-3.5 hover:border-primary/20 transition-all duration-155">
                    <Badge variant="outline" className="shrink-0 mt-0.5 font-mono bg-background/50">
                      {i + 1}
                    </Badge>
                    <span className="font-semibold text-foreground/90">{t}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 2. 简介生成 */}
        <Card className="glass-card border-border/40 hover:border-primary/10 transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold">
              <FileEdit className="h-5 w-5 text-purple-400" />
              AI 吸引力简介生成
            </CardTitle>
            <CardDescription>
              采用「核心冲突 + 金手指设定 + 爽点预告 + 悬念钩子」四部曲公式自动润色生成
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleGenBlurb}
              disabled={platformLoading === "blurb"}
              className="w-full shadow-md shadow-primary/15"
            >
              {platformLoading === "blurb" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4 mr-2" />
              )}
              生成简介版本
            </Button>
            {blurbs.length > 0 && (
              <div className="space-y-3.5 pt-2 border-t border-border/20 max-h-[350px] overflow-y-auto pr-1">
                {blurbs.map((b, i) => (
                  <div key={i} className="p-4 rounded-xl border border-border/45 bg-muted/10">
                    <p className="text-xs text-muted-foreground/80 font-bold mb-1.5 uppercase tracking-wide">版本 {i + 1}</p>
                    <p className="text-xs leading-relaxed text-foreground/80 whitespace-pre-wrap font-serif">{b}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 3. 开篇与章节钩子检测 */}
        <Card className="glass-card border-border/40 hover:border-primary/10 transition-all duration-300 md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold">
              <Target className="h-5 w-5 text-emerald-400 animate-pulse" />
              开篇 & 章节结尾钩子综合检测
            </CardTitle>
            <CardDescription>
              重点诊断前200字冲突吸引力，及章节结尾是否留下足够的追读悬念，这关系到平台算法推荐权重。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3 flex-wrap bg-secondary/15 p-3 rounded-xl border border-border/20">
              <span className="text-xs font-semibold text-muted-foreground">章节号：</span>
              <Input
                type="number"
                value={hookChapterNum}
                onChange={(e) => setHookChapterNum(Math.max(1, Number(e.target.value) || 1))}
                className="w-20 h-8 font-semibold text-center hover:border-primary/20"
                min={1}
              />
              <Button
                onClick={() => handleWorkbenchOpeningHook(hookChapterNum)}
                disabled={platformLoading === "hook" || platformLoading === "workbenchOpening"}
                variant="outline"
                size="sm"
                className="h-8 text-xs hover:bg-accent/40"
              >
                {platformLoading === "hook" || platformLoading === "workbenchOpening" ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Target className="h-3.5 w-3.5 mr-1.5 text-emerald-400" />
                )}
                诊断开篇吸引力
              </Button>
              <Button
                onClick={() => handleGenSelectedChapterTitle(hookChapterNum)}
                disabled={platformLoading === "chapterTitle" || platformLoading === "workbenchTitle"}
                variant="outline"
                size="sm"
                className="h-8 text-xs hover:bg-accent/40"
              >
                {platformLoading === "chapterTitle" || platformLoading === "workbenchTitle" ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <FileEdit className="h-3.5 w-3.5 mr-1.5 text-blue-400" />
                )}
                生成章节标题建议
              </Button>
              <Separator orientation="vertical" className="h-6 hidden sm:block" />
              <Button
                onClick={handleBatchHookCheck}
                disabled={platformLoading === "batch"}
                variant="outline"
                size="sm"
                className="h-8 text-xs hover:bg-accent/40"
              >
                {platformLoading === "batch" ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5 text-purple-400" />
                )}
                批量检测所有章节结尾钩子
              </Button>
            </div>

            {hookResult && (
              <div className="p-4 rounded-xl border border-border/40 space-y-3.5 bg-card/25">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm">开篇吸引力评分：</span>
                  <Badge variant={(hookResult.score || 0) >= 7 ? "default" : "destructive"} className="font-bold">
                    {hookResult.score} / 10 分
                  </Badge>
                  {hookResult.hook_strength && (
                    <Badge variant="outline" className="border-border bg-background/50 font-medium">
                      强度: {hookResult.hook_strength}
                    </Badge>
                  )}
                </div>
                {hookResult.issues && hookResult.issues.length > 0 && (
                  <div className="text-xs text-muted-foreground leading-relaxed">
                    <span className="text-destructive/80 font-bold block mb-1">主要存在问题：</span>
                    {hookResult.issues.map((issue: string, i: number) => (
                      <p key={i} className="ml-2 flex items-start gap-1">
                        <span className="text-muted-foreground/45 select-none">•</span>
                        <span>{issue}</span>
                      </p>
                    ))}
                  </div>
                )}
                {hookResult.rewrite_suggestion && (
                  <p className="text-xs text-muted-foreground leading-relaxed bg-muted/5 border border-border/30 rounded-lg p-2.5">
                    <span className="font-bold text-foreground/90 block mb-1">改写优化建议：</span>
                    {hookResult.rewrite_suggestion}
                  </p>
                )}
                {(hookResult as any).rewritten_opening && (
                  <div className="p-4 rounded-xl border border-border/40 bg-muted/10 text-xs">
                    <p className="text-[11px] text-muted-foreground/80 font-bold mb-2 uppercase tracking-wide">润色示例（前200字对照）：</p>
                    <p className="font-serif leading-7 text-foreground/90 whitespace-pre-wrap pl-1">{(hookResult as any).rewritten_opening}</p>
                  </div>
                )}
              </div>
            )}

            {chapterTitles.length > 0 && (
              <div className="space-y-2 p-4 rounded-xl border border-border/40 bg-muted/10">
                <p className="text-xs text-muted-foreground/80 font-bold mb-2">第 {hookChapterNum} 章章节标题建议：</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {chapterTitles.map((t, i) => (
                    <div key={i} className="text-xs font-semibold px-3 py-2 bg-background/50 rounded-lg border border-border/30 text-foreground/95">
                      「{t}」
                    </div>
                  ))}
                </div>
              </div>
            )}

            {batchHookResult.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border/20 max-h-60 overflow-y-auto pr-1">
                <p className="text-xs font-bold text-muted-foreground mb-2">章节结尾钩子检查日志：</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {batchHookResult.map((r: any) => (
                    <div key={r.chapter_number} className="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-border/40 bg-card/25 text-xs">
                      <span className="font-mono text-muted-foreground/85 font-semibold">第 {r.chapter_number} 章</span>
                      <div className="flex items-center gap-2 min-w-0">
                        {r.analysis?.hook_type && <span className="text-muted-foreground truncate max-w-[120px]">{r.analysis.hook_type}</span>}
                        <Badge
                          variant={r.analysis?.has_hook ? "default" : "destructive"}
                          className={r.analysis?.has_hook ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[9px] shrink-0" : "bg-destructive/10 text-destructive border-destructive/20 text-[9px] shrink-0"}
                        >
                          {r.analysis?.has_hook ? "有钩子" : "缺钩子"}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 4. 标签生成 */}
        <Card className="glass-card border-border/40 hover:border-primary/10 transition-all duration-300 md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold">
              <Tag className="h-5 w-5 text-indigo-400" />
              平台搜索标签 & 流量关键词
            </CardTitle>
            <CardDescription>
              按推荐算法的曝光偏好，为小说匹配最利于检索的核心分类标签和次级关联标签词汇。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleGenTags}
              disabled={platformLoading === "tags"}
              className="w-full shadow-md shadow-primary/15"
            >
              {platformLoading === "tags" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4 mr-2" />
              )}
              一键预测标签
            </Button>
            {tagsResult && (
              <div className="space-y-4 pt-3 border-t border-border/20">
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground">主标签（建议直接选用）：</p>
                  <div className="flex flex-wrap gap-2">
                    {tagsResult.main_tags?.map((t: string, i: number) => (
                      <Badge key={i} className="cursor-default bg-primary/20 text-primary border-primary/25 font-semibold text-xs px-2.5 py-0.5">
                        {t}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground">搜索关联词（推荐写入作品标签后台）：</p>
                  <div className="flex flex-wrap gap-1.5">
                    {tagsResult.search_keywords?.map((k: string, i: number) => (
                      <Badge key={i} variant="secondary" className="cursor-default text-xs font-medium bg-secondary/80 text-muted-foreground">
                        {k}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-border/10">
                  {tagsResult.category_recommendation && (
                    <div className="p-3.5 rounded-xl border border-border/40 bg-muted/10 text-xs">
                      <span className="text-muted-foreground/80 block mb-1">建议发布分区:</span>
                      <span className="font-bold text-foreground">{tagsResult.category_recommendation}</span>
                    </div>
                  )}
                  {tagsResult.target_audience && (
                    <div className="p-3.5 rounded-xl border border-border/40 bg-muted/10 text-xs">
                      <span className="text-muted-foreground/80 block mb-1">画像定位核心受众:</span>
                      <span className="font-semibold text-foreground/90 leading-relaxed">{tagsResult.target_audience}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
