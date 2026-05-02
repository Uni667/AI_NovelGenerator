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
import { ChevronLeft, ChevronRight, Save, PenLine, CheckCircle, Loader2, Play } from "lucide-react"

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
    await api.chapters.update(projectId, chapterNum, { content })
    toast.success("已保存")
    setIsEditing(false)
  }

  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

  const handleGenerate = () => {
    connect(`${base}/api/v1/projects/${projectId}/generate/chapter/${chapterNum}?t=${Date.now()}`)
  }

  const handleFinalize = () => {
    connect(`${base}/api/v1/projects/${projectId}/generate/finalize/${chapterNum}?t=${Date.now()}`)
  }

  const isDone = events.some(e => e.type === "done")

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

  if (isLoading) return <div className="text-center py-12 text-muted-foreground">加载中...</div>

  return (
    <div className="flex gap-6 h-[calc(100vh-6rem)]">
      {/* 左侧章节内容 */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" disabled={!prevChapter} onClick={() => router.push(`/projects/${projectId}/chapter/${chapterNum - 1}`)}>
              <ChevronLeft className="h-5 w-5" />
            </Button>
            <h1 className="text-xl font-bold">
              第{chapterNum}章 {chapterData?.meta?.chapter_title || ""}
            </h1>
            <Button variant="ghost" size="icon" disabled={!nextChapter} onClick={() => router.push(`/projects/${projectId}/chapter/${chapterNum + 1}`)}>
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex items-center gap-2">
            {chapterData?.meta && (
              <Badge variant={chapterData.meta.status === "final" ? "default" : "secondary"}>
                {chapterData.meta.status === "final" ? "已定稿" : "草稿"}
              </Badge>
            )}
            <Badge variant="outline">{chapterData?.meta?.word_count || content.length} 字</Badge>
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

        {/* 内容区 */}
        <div className="flex-1 border rounded-lg overflow-hidden">
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
        <div className="flex items-center gap-3 mt-4">
          {isEditing ? (
            <>
              <Button onClick={handleSave}><Save className="h-4 w-4 mr-2" />保存</Button>
              <Button variant="outline" onClick={() => setIsEditing(false)}>取消</Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setIsEditing(true)} disabled={isConnected}>
                <PenLine className="h-4 w-4 mr-2" />编辑
              </Button>
              <Button onClick={handleGenerate} disabled={isConnected}>
                <Play className="h-4 w-4 mr-2" />AI 生成本章
              </Button>
              {content && chapterData?.meta?.status !== "final" && (
                <Button onClick={handleFinalize} disabled={isConnected} variant="secondary">
                  <CheckCircle className="h-4 w-4 mr-2" />定稿
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* 右侧章节信息 */}
      <div className="w-72 shrink-0 space-y-4">
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
