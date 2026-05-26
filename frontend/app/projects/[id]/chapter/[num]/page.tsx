"use client"

import { useParams, useRouter } from "next/navigation"
import { useChapter, useChapters } from "@/lib/hooks/use-projects"
import { useSSE } from "@/lib/hooks/use-sse"
import { api } from "@/lib/api-client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { useState, useEffect } from "react"
import { toast } from "sonner"
import { AlertCircle, ChevronLeft, ChevronRight, Save, PenLine, CheckCircle, Loader2, Play, ArrowLeft } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"

export default function ChapterPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const chapterNum = parseInt(params.num as string)
  const { data: chapters } = useChapters(projectId)
  const { data: chapterData, isLoading } = useChapter(projectId, chapterNum)
  const { events, isConnected, connect } = useSSE()
  const [content, setContent] = useState("")
  const [isEditing, setIsEditing] = useState(false)

  useEffect(() => {
    if (chapterData?.content) setContent(chapterData.content)
  }, [chapterData])

  const handleSave = async () => {
    try {
      await api.chapters.update(projectId, chapterNum, { content })
      toast.success("已保存")
      setIsEditing(false)
    } catch {
      toast.error("保存失败，请重试")
    }
  }

  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

  const handleGenerate = () => {
    connect(`${base}/api/v1/projects/${projectId}/generate/chapter/${chapterNum}?t=${Date.now()}`)
  }

  const handleFinalize = () => {
    connect(`${base}/api/v1/projects/${projectId}/generate/finalize/${chapterNum}?t=${Date.now()}`)
  }

  const isDone = events.some(e => e.type === "done")
  const lastError = events.filter(e => e.type === "error").pop()

  useEffect(() => {
    if (isDone) {
      // 重新加载章节内容
      api.chapters.get(projectId, chapterNum).then(d => {
        if (d?.content) setContent(d.content)
      })
    }
  }, [chapterNum, isDone, projectId])

  const prevChapter = chapters?.find((c: any) => c.chapter_number === chapterNum - 1)
  const nextChapter = chapters?.find((c: any) => c.chapter_number === chapterNum + 1)

  if (isLoading) {
    return (
      <div className="flex gap-6 h-[calc(100vh-6rem)] animate-pulse">
        {/* Left column loading skeleton */}
        <div className="flex-1 flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-border/10 pb-4">
            <div className="flex items-center gap-3">
              <Skeleton className="h-8 w-24 bg-muted/40 rounded-xl" />
              <Separator orientation="vertical" className="h-4 bg-border/20" />
              <Skeleton className="h-8 w-8 bg-muted/40 rounded-full" />
              <Skeleton className="h-7 w-48 bg-muted/50 rounded-xl" />
              <Skeleton className="h-8 w-8 bg-muted/40 rounded-full" />
            </div>
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-16 bg-muted/40 rounded-full" />
              <Skeleton className="h-6 w-20 bg-muted/40 rounded-full" />
            </div>
          </div>
          <div className="flex-1 border border-border/30 rounded-2xl p-6 bg-card/10 backdrop-blur-md space-y-4">
            <Skeleton className="h-6 w-1/4 bg-muted/40 rounded-lg" />
            <div className="space-y-3">
              <Skeleton className="h-4 w-full bg-muted/30 rounded-md" />
              <Skeleton className="h-4 w-11/12 bg-muted/30 rounded-md" />
              <Skeleton className="h-4 w-full bg-muted/30 rounded-md" />
              <Skeleton className="h-4 w-4/5 bg-muted/30 rounded-md" />
              <Skeleton className="h-4 w-full bg-muted/30 rounded-md" />
              <Skeleton className="h-4 w-3/4 bg-muted/30 rounded-md" />
            </div>
          </div>
          <div className="flex items-center gap-3 mt-2">
            <Skeleton className="h-9 w-20 bg-muted/40 rounded-xl" />
            <Skeleton className="h-9 w-32 bg-muted/40 rounded-xl" />
          </div>
        </div>

        {/* Right column loading skeleton */}
        <div className="w-72 shrink-0 space-y-4">
          <div className="border border-border/30 rounded-2xl p-4 bg-card/10 backdrop-blur-md space-y-3">
            <Skeleton className="h-4 w-20 bg-muted/40 rounded-lg" />
            <Separator className="bg-border/20" />
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex flex-col gap-1.5">
                <Skeleton className="h-3 w-12 bg-muted/40 rounded" />
                <Skeleton className="h-4 w-full bg-muted/30 rounded" />
              </div>
            ))}
          </div>

          <div className="border border-border/30 rounded-2xl p-4 bg-card/10 backdrop-blur-md space-y-3">
            <Skeleton className="h-4 w-20 bg-muted/40 rounded-lg" />
            <Separator className="bg-border/20" />
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full bg-muted/20 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-auto lg:h-[calc(100vh-6rem)]">
      {/* 左侧章节内容 */}
      <div className="flex-1 flex flex-col min-h-[500px] lg:min-h-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4 shrink-0">
          <div className="flex flex-wrap items-center gap-2 md:gap-3 min-w-0">
            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-muted-foreground hover:text-foreground shrink-0" onClick={() => router.push(`/projects/${projectId}`)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              返回项目
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4 bg-border shrink-0" />
            <div className="flex items-center gap-1 shrink-0">
              <Button variant="ghost" size="icon" className="h-8 w-8" disabled={!prevChapter} onClick={() => router.push(`/projects/${projectId}/chapter/${chapterNum - 1}`)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-base sm:text-lg font-bold truncate max-w-[150px] sm:max-w-xs">
                第{chapterNum}章 {chapterData?.meta?.chapter_title || ""}
              </h1>
              <Button variant="ghost" size="icon" className="h-8 w-8" disabled={!nextChapter} onClick={() => router.push(`/projects/${projectId}/chapter/${chapterNum + 1}`)}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {chapterData?.meta && (
              <Badge variant={chapterData.meta.status === "final" ? "default" : "secondary"} className="text-[10px] px-2 py-0.5">
                {chapterData.meta.status === "final" ? "已定稿" : "草稿"}
              </Badge>
            )}
            <Badge variant="outline" className="text-[10px] px-2 py-0.5">{chapterData?.meta?.word_count || content.length} 字</Badge>
          </div>
        </div>

        {/* 生成进度 */}
        {isConnected && (
          <div className="flex items-center gap-2 mb-2 text-primary">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">AI 正在生成...</span>
          </div>
        )}
        {events.filter(e => e.type === "progress").map((e, i) => (
          <div key={i} className="flex items-center gap-2 mb-1 text-sm text-muted-foreground">
            <CheckCircle className="h-3 w-3 text-green-500" />
            {e.data.message}
          </div>
        ))}
        {lastError && (
          <div className="flex items-start gap-2 mb-2 rounded-lg bg-destructive/10 p-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{lastError.data?.message || "生成失败"}</span>
          </div>
        )}

        {/* 内容区 */}
        <div className="flex-1 border rounded-lg overflow-hidden h-[50vh] lg:h-auto min-h-[300px]">
          {isEditing ? (
            <Textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              className="h-full resize-none font-serif text-base leading-relaxed p-6"
              placeholder="在此编写章节内容..."
            />
          ) : (
            <ScrollArea className="h-full">
              <div className="p-6 font-serif text-base leading-relaxed whitespace-pre-wrap">
                {content || (
                  <div className="text-center py-16 text-muted-foreground">
                    <PenLine className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>本章暂无内容</p>
                    <p className="text-sm mt-1">点击下方按钮生成或手动编写</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex flex-wrap items-center gap-3 mt-4">
          {isEditing ? (
            <>
              <Button onClick={handleSave} className="w-full sm:w-auto"><Save className="h-4 w-4 mr-2" />保存</Button>
              <Button variant="outline" onClick={() => setIsEditing(false)} className="w-full sm:w-auto">取消</Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setIsEditing(true)} disabled={isConnected} className="w-full sm:w-auto">
                <PenLine className="h-4 w-4 mr-2" />编辑
              </Button>
              <Button onClick={handleGenerate} disabled={isConnected} className="w-full sm:w-auto">
                <Play className="h-4 w-4 mr-2" />AI 生成本章
              </Button>
              {content && chapterData?.meta?.status !== "final" && (
                <Button onClick={handleFinalize} disabled={isConnected} variant="secondary" className="w-full sm:w-auto">
                  <CheckCircle className="h-4 w-4 mr-2" />定稿
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* 右侧章节信息 */}
      <div className="w-full lg:w-72 shrink-0 space-y-4 pb-6 lg:pb-0">
        {chapterData?.meta && (
          <Card>
            <CardHeader><CardTitle className="text-sm">章节信息</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div><span className="text-muted-foreground">定位：</span>{chapterData.meta.chapter_role || "-"}</div>
              <div><span className="text-muted-foreground">核心作用：</span>{chapterData.meta.chapter_purpose || "-"}</div>
              <div><span className="text-muted-foreground">悬念密度：</span>{chapterData.meta.suspense_level || "-"}</div>
              <div><span className="text-muted-foreground">伏笔操作：</span>{chapterData.meta.foreshadowing || "-"}</div>
              <div><span className="text-muted-foreground">认知颠覆：</span>{chapterData.meta.plot_twist_level || "-"}</div>
              <Separator />
              <div><span className="text-muted-foreground">简述：</span>{chapterData.meta.chapter_summary || "-"}</div>
            </CardContent>
          </Card>
        )}

        {/* 章节目录导航 */}
        <Card>
          <CardHeader><CardTitle className="text-sm">章节目录</CardTitle></CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-96">
              <div className="p-2 space-y-1">
                {chapters?.map((ch: any) => (
                  <Button
                    key={ch.chapter_number}
                    variant={ch.chapter_number === chapterNum ? "secondary" : "ghost"}
                    className="w-full justify-start text-sm"
                    onClick={() => router.push(`/projects/${projectId}/chapter/${ch.chapter_number}`)}
                  >
                    <span className="font-mono mr-2 text-xs">第{ch.chapter_number}章</span>
                    <span className="truncate">{ch.chapter_title || "未命名"}</span>
                  </Button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
