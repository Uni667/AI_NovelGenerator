"use client"

import { useParams, useRouter } from "next/navigation"
import { useProject, useProjectConfig, useChapters, useUpdateProjectConfig } from "@/lib/hooks/use-projects"
import { useSSE } from "@/lib/hooks/use-sse"
import { api } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { useState, useEffect } from "react"
import { toast } from "sonner"
import { Play, FileText, BookOpen, Upload, Trash2, CheckCircle, AlertCircle, Loader2, ChevronLeft, ChevronRight } from "lucide-react"

export default function ProjectDashboard() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { data: project } = useProject(id)
  const { data: config } = useProjectConfig(id)
  const { data: chapters } = useChapters(id)
  const updateConfig = useUpdateProjectConfig(id)
  const { events, isConnected, connect } = useSSE()

  const [activeTab, setActiveTab] = useState("overview")
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null)

  const lastProgress = events.filter(e => e.type === "progress").pop()
  const lastPartial = events.filter(e => e.type === "partial").pop()
  const hasError = events.some(e => e.type === "error")

  const handleGenerateArchitecture = () => {
    setActiveTab("generation")
    connect(`http://localhost:8001/api/v1/projects/${id}/generate/architecture?t=${Date.now()}`)
  }

  const handleGenerateBlueprint = () => {
    setActiveTab("generation")
    connect(`http://localhost:8001/api/v1/projects/${id}/generate/blueprint?t=${Date.now()}`)
  }

  const handleUploadKnowledge = async () => {
    if (!knowledgeFile) return
    const result = await api.knowledge.upload(id, knowledgeFile)
    toast.success(result.message || "上传成功")
    setKnowledgeFile(null)
  }

  if (!project) return <div className="text-center py-12 text-muted-foreground">加载中...</div>

  return (
    <div>
      {/* 顶部标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="text-muted-foreground">{project.description || "暂无简介"}</p>
        </div>
        <Badge variant={project.status === "ready" ? "default" : "secondary"} className="text-sm px-3 py-1">
          {project.status === "draft" ? "草稿" : project.status === "ready" ? "就绪" : project.status}
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="generation">AI 生成</TabsTrigger>
          <TabsTrigger value="knowledge">知识库</TabsTrigger>
          <TabsTrigger value="settings">参数设置</TabsTrigger>
        </TabsList>

        {/* 概览 Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">总章节</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{config?.num_chapters || 0}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">已完成</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{chapters?.filter((c: any) => c.status === "final").length || 0}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">类型</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.genre || "-"}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">每章字数</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.word_number || "-"}</span></CardContent>
            </Card>
          </div>

          {/* 快速操作 */}
          <Card>
            <CardHeader><CardTitle>快速操作</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button onClick={handleGenerateArchitecture} disabled={isConnected}>
                <Play className="h-4 w-4 mr-2" />生成架构
              </Button>
              <Button onClick={handleGenerateBlueprint} disabled={isConnected} variant="outline">
                <FileText className="h-4 w-4 mr-2" />生成章节目录
              </Button>
            </CardContent>
          </Card>

          {/* 章节列表 */}
          <Card>
            <CardHeader><CardTitle>章节列表</CardTitle></CardHeader>
            <CardContent>
              {!chapters?.length ? (
                <p className="text-muted-foreground text-sm">尚未生成章节目录，请先执行「生成架构」→「生成章节目录」</p>
              ) : (
                <ScrollArea className="h-64">
                  <div className="space-y-2">
                    {chapters.map((ch: any) => (
                      <div
                        key={ch.chapter_number}
                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer"
                        onClick={() => router.push(`/projects/${id}/chapter/${ch.chapter_number}`)}
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm text-muted-foreground">第{ch.chapter_number}章</span>
                          <span className="font-medium">{ch.chapter_title || "未命名"}</span>
                          {ch.chapter_summary && (
                            <span className="text-sm text-muted-foreground truncate max-w-xs">{ch.chapter_summary}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          {ch.word_count > 0 && <span className="text-xs text-muted-foreground">{ch.word_count}字</span>}
                          <Badge variant={ch.status === "final" ? "default" : "secondary"}>
                            {ch.status === "final" ? "已定稿" : ch.status === "draft" ? "草稿" : "待生成"}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI 生成 Tab */}
        <TabsContent value="generation">
          <Card>
            <CardHeader>
              <CardTitle>AI 生成进度</CardTitle>
              <CardDescription>实时显示生成状态</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {events.length === 0 && !isConnected && (
                <div className="text-center py-8 text-muted-foreground">
                  <Play className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>点击上方的「生成架构」或「生成章节目录」开始</p>
                </div>
              )}

              {isConnected && (
                <div className="flex items-center gap-2 text-primary">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>AI 正在生成中...</span>
                </div>
              )}

              {events.filter(e => e.type === "progress").map((e, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  {e.data.status === "done" ? (
                    <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                  ) : (
                    <Loader2 className="h-5 w-5 animate-spin text-primary mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium">{e.data.message}</p>
                    <p className="text-xs text-muted-foreground">步骤: {e.data.step}</p>
                  </div>
                </div>
              ))}

              {hasError && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-destructive/10 text-destructive">
                  <AlertCircle className="h-5 w-5 mt-0.5" />
                  <p>生成过程中出现错误，请查看日志</p>
                </div>
              )}

              {lastPartial && (
                <div className="p-4 rounded-lg border bg-muted/30">
                  <p className="text-xs text-muted-foreground mb-2">生成预览：</p>
                  <pre className="text-sm whitespace-pre-wrap font-sans">{lastPartial.data.content}</pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 知识库 Tab */}
        <TabsContent value="knowledge">
          <Card>
            <CardHeader>
              <CardTitle>知识库管理</CardTitle>
              <CardDescription>上传 TXT 设定文档，AI 会在生成章节时自动检索相关内容。创建项目后，先上传大纲再生成架构效果更好。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Input type="file" accept=".txt,.md" onChange={e => setKnowledgeFile(e.target.files?.[0] || null)} />
                <Button onClick={handleUploadKnowledge} disabled={!knowledgeFile}>
                  <Upload className="h-4 w-4 mr-2" />上传并导入
                </Button>
              </div>
              <Separator />
              <Button variant="destructive" onClick={async () => { await api.knowledge.clearVector(id); toast.success("向量库已清空") }}>
                <Trash2 className="h-4 w-4 mr-2" />清空向量库
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 参数设置 Tab */}
        <TabsContent value="settings">
          <Card>
            <CardHeader><CardTitle>项目参数</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>类型</Label>
                  <Input defaultValue={config?.genre} onBlur={e => updateConfig.mutate({ genre: e.target.value })} />
                </div>
                <div>
                  <Label>主题</Label>
                  <Input defaultValue={config?.topic} onBlur={e => updateConfig.mutate({ topic: e.target.value })} />
                </div>
                <div>
                  <Label>章节数</Label>
                  <Input type="number" defaultValue={config?.num_chapters} onBlur={e => updateConfig.mutate({ num_chapters: +e.target.value })} />
                </div>
                <div>
                  <Label>每章字数</Label>
                  <Input type="number" defaultValue={config?.word_number} onBlur={e => updateConfig.mutate({ word_number: +e.target.value })} />
                </div>
              </div>
              <div>
                <Label>内容指导（大纲）</Label>
                <Textarea
                  defaultValue={config?.user_guidance}
                  rows={8}
                  onBlur={e => updateConfig.mutate({ user_guidance: e.target.value })}
                  placeholder="在这里描述你的大纲、世界观、角色构想..."
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
