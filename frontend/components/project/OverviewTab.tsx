"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Play, FileText, FileDown, BookOpen } from "lucide-react"
import { ArchitectureStatusCard } from "@/components/files/ArchitectureStatusCard"
import { OutlineStatusCard } from "@/components/files/OutlineStatusCard"
import { Progress } from "@/components/ui/progress"
import { api } from "@/lib/api-client"
import { PLATFORM_CONFIG } from "@/lib/types"
import { useRouter } from "next/navigation"
import { useProjectContext } from "./ProjectContext"
import { useState, useCallback, useEffect } from "react"
import type { Chapter, ProjectFile } from "@/lib/types"
import { toast } from "sonner"

export function OverviewTab() {
  const router = useRouter()
  const { projectId, config, chapters, generation, setActiveTab, setSelectedOutputFile } = useProjectContext()
  const { isConnected, generationTaskId, generationStopping, generationTaskLabel, generationProgress, startTask } = generation

  const completedChapters = chapters?.filter((c: Chapter) => c.status === "final").length || 0
  const draftChapters = chapters?.filter((c: Chapter) => c.status === "draft").length || 0

  const [architectureFile, setArchitectureFile] = useState<ProjectFile | null>(null)
  const [outlineFile, setOutlineFile] = useState<ProjectFile | null>(null)
  const [archOutlineLoading, setArchOutlineLoading] = useState(true)


  const loadArchitectureAndOutline = useCallback(async () => {
    if (!projectId) return
    setArchOutlineLoading(true)
    try {
      const [arch, outline] = await Promise.all([
        api.projectFiles.getCurrentArchitecture(projectId),
        api.projectFiles.getCurrentOutline(projectId),
      ])
      setArchitectureFile(arch)
      setOutlineFile(outline)
    } catch (e) {
      console.error(e)
    } finally {
      setArchOutlineLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadArchitectureAndOutline()
  }, [loadArchitectureAndOutline])

  const handleGenerateArchitecture = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      startTask("architecture", `/api/v1/projects/${projectId}/generate/architecture`, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateBlueprint = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      startTask("blueprint", `/api/v1/projects/${projectId}/generate/blueprint`, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  return (
    <div className="space-y-6">
      {(isConnected || generationTaskId) && (
        <Card className="border border-primary/30 bg-primary/5 shadow-lg shadow-primary/5 rounded-xl p-4 animate-glow-pulse">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                <h4 className="text-sm font-bold text-foreground">AI 任务正在运行</h4>
              </div>
              <p className="text-xs text-muted-foreground">{generationTaskLabel || "准备生成中..."}</p>
            </div>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 animate-pulse text-xs">
              {generationStopping ? "正在中断..." : "进行中"}
            </Badge>
          </div>
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-[10px] text-muted-foreground">
              <span>估计总进度</span>
              <span className="font-mono font-bold text-primary">{generationProgress}%</span>
            </div>
            <Progress value={generationProgress} className="w-full text-xs" />
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <Card className="glass-card border-border/50 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-primary/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">总章节</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-extrabold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
              {config?.num_chapters || 0}
            </span>
          </CardContent>
        </Card>
        <Card className="glass-card border-border/50 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-emerald-400/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-400/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-extrabold text-emerald-400">{completedChapters}</span>
          </CardContent>
        </Card>
        <Card className="glass-card border-border/50 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-amber-400/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-400/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">草稿章节</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-extrabold text-amber-400">{draftChapters}</span>
          </CardContent>
        </Card>
        <Card className="glass-card border-border/50 col-span-2 sm:col-span-1 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-primary/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">目标平台</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-bold flex items-center gap-1.5 truncate">
              {config?.platform ? (
                <>
                  <span className="text-xl shrink-0">{PLATFORM_CONFIG[config.platform]?.icon}</span>
                  <span className="truncate">{PLATFORM_CONFIG[config.platform]?.label}</span>
                </>
              ) : (
                "-"
              )}
            </span>
          </CardContent>
        </Card>
        <Card className="glass-card border-border/50 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-primary/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">分类</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-bold">{config?.category || "-"}</span>
          </CardContent>
        </Card>
        <Card className="glass-card border-border/50 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-primary/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">风格/流派</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-bold">{config?.genre || "-"}</span>
          </CardContent>
        </Card>
        <Card className="glass-card border-border/50 transition-all duration-300 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.15)] hover:border-primary/40 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">每章字数</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-bold">{config?.word_number ? `${config.word_number}字` : "-"}</span>
          </CardContent>
        </Card>
      </div>

      <Card className="glass-panel border-border/40">
        <CardHeader>
          <CardTitle className="text-lg font-bold tracking-tight">快速操作</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button
            onClick={handleGenerateArchitecture}
            disabled={isConnected || Boolean(generationTaskId) || generationStopping}
            className="shadow-md shadow-primary/20 hover:scale-102 transition-transform duration-200"
          >
            <Play className="h-4 w-4 mr-2" />生成架构
          </Button>
          <Button
            onClick={handleGenerateBlueprint}
            disabled={isConnected || Boolean(generationTaskId) || generationStopping}
            variant="outline"
            className="hover:bg-accent/40"
          >
            <FileText className="h-4 w-4 mr-2" />生成章节目录
          </Button>
          <Separator orientation="vertical" className="h-9 hidden md:block" />
          <Button variant="outline" onClick={() => api.export.download(projectId, "txt")} className="hover:bg-accent/40">
            <FileDown className="h-4 w-4 mr-2 text-indigo-400" />导出 TXT
          </Button>
          <Button variant="outline" onClick={() => api.export.download(projectId, "html")} className="hover:bg-accent/40">
            <FileDown className="h-4 w-4 mr-2 text-blue-400" />导出 HTML
          </Button>
          <Button variant="outline" onClick={() => setActiveTab("files")} className="hover:bg-accent/40">
            <FileText className="h-4 w-4 mr-2 text-purple-400" />查看生成文件
          </Button>
          <Button variant="outline" onClick={() => setActiveTab("workbench")} className="hover:bg-accent/40">
            <BookOpen className="h-4 w-4 mr-2 text-emerald-400" />进入章节工作台
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ArchitectureStatusCard
          architecture={architectureFile}
          isLoading={archOutlineLoading}
          onImport={() => {
            toast.info("导入功能处于规划中，暂未启用")
          }}
          onRegenerate={handleGenerateArchitecture}
          onPreview={() => {
            setSelectedOutputFile("Novel_architecture.txt")
            setActiveTab("files")
          }}
        />
        <OutlineStatusCard
          outline={outlineFile}
          hasArchitecture={!!architectureFile}
          isLoading={archOutlineLoading}
          onImport={() => {
            toast.info("导入功能处于规划中，暂未启用")
          }}
          onRegenerate={handleGenerateBlueprint}
          onPreview={() => {
            setSelectedOutputFile("Novel_directory.txt")
            setActiveTab("files")
          }}
        />
      </div>

      <Card className="glass-panel border-border/40">
        <CardHeader>
          <CardTitle className="text-lg font-bold tracking-tight">章节列表</CardTitle>
        </CardHeader>
        <CardContent>
          {!chapters?.length ? (
            <p className="text-muted-foreground text-sm py-4">尚未生成章节目录，请先执行「生成架构」→「生成章节目录」</p>
          ) : (
            <ScrollArea className="h-64 pr-2">
              <div className="space-y-2">
                {chapters.map((ch: any) => (
                  <div
                    key={ch.chapter_number}
                    className="flex items-center justify-between p-3.5 rounded-xl border border-border/65 bg-card/20 hover:bg-accent/30 hover:border-primary/20 hover:translate-x-0.5 transition-all duration-200 cursor-pointer"
                    onClick={() => router.push(`/projects/${projectId}/chapter/${ch.chapter_number}`)}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="font-mono text-xs text-muted-foreground bg-secondary/80 px-2 py-0.5 rounded-md shrink-0">
                        第{ch.chapter_number}章
                      </span>
                      <span className="font-semibold text-sm truncate">{ch.chapter_title || "未命名"}</span>
                      {ch.chapter_summary && (
                        <span className="text-xs text-muted-foreground truncate hidden md:block max-w-sm ml-2">
                          {ch.chapter_summary}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-2">
                      {ch.word_count > 0 && <span className="text-xs text-muted-foreground hidden sm:inline">{ch.word_count}字</span>}
                      <Badge
                        variant={ch.status === "final" ? "default" : "secondary"}
                        className={
                          ch.status === "final"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : ch.status === "draft"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-secondary text-muted-foreground"
                        }
                      >
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
    </div>
  )
}
