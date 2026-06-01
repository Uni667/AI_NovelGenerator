"use client"

import { Suspense, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useProjects, useDeleteProject } from "@/lib/hooks/use-projects"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Plus, Trash2, BookOpen, RefreshCw, AlertTriangle } from "lucide-react"
import { toast } from "sonner"

import { ProjectCard } from "@/components/home/ProjectCard"
import { ProjectStats } from "@/components/home/ProjectStats"
import { CreateProjectDialog } from "@/components/home/CreateProjectDialog"
import { ModelConfigDialog } from "@/components/home/ModelConfigDialog"
import { DataMigrationDialog } from "@/components/home/DataMigrationDialog"
import { projectService } from "@/lib/services/projectService"

function HomeContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const searchQuery = searchParams?.get("search") || ""

  const { data: projects, isLoading, isError, error, refetch } = useProjects()
  const deleteProject = useDeleteProject()
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  
  const [createOpen, setCreateOpen] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
  const [migrationOpen, setMigrationOpen] = useState(false)

  const stats = projectService.calculateStats(projects || [])

  const filteredProjects = projects?.filter((p: any) => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return true
    return (
      p.name.toLowerCase().includes(q) ||
      (p.genre && p.genre.toLowerCase().includes(q)) ||
      (p.description && p.description.toLowerCase().includes(q)) ||
      (p.platform && p.platform.toLowerCase().includes(q))
    )
  })

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await deleteProject.mutateAsync(deleteTarget)
      toast.success("项目已成功从底座中移除！")
    } catch (err: any) {
      toast.error(err?.message || "删除项目失败，请重试")
    } finally {
      setDeleteTarget(null)
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto space-y-8 pb-10">
        <Skeleton className="h-[210px] w-full rounded-3xl bg-card/40 border border-border/40" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Skeleton className="h-24 rounded-2xl bg-card/40" />
          <Skeleton className="h-24 rounded-2xl bg-card/40" />
          <Skeleton className="h-24 rounded-2xl bg-card/40" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="glass-card border border-border/40 p-5 rounded-2xl h-[210px] space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Skeleton className="h-5 w-2/3 rounded-lg" />
                  <Skeleton className="h-5 w-12 rounded-full" />
                </div>
                <Skeleton className="h-4 w-full rounded-md" />
                <Skeleton className="h-4 w-5/6 rounded-md" />
              </div>
              <div className="flex justify-between items-center">
                <Skeleton className="h-4 w-24 rounded-md" />
                <Skeleton className="h-7 w-7 rounded-md" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-md mx-auto py-16 text-center">
        <Card className="glass-panel border-rose-500/20 bg-rose-500/5 p-6 rounded-3xl">
          <CardContent className="space-y-4 pt-6">
            <div className="h-16 w-16 mx-auto rounded-full bg-rose-500/10 flex items-center justify-center text-rose-400 border border-rose-500/20">
              <AlertTriangle className="h-8 w-8" />
            </div>
            <h2 className="text-xl font-bold text-foreground">算力节点连接失败</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {error instanceof Error ? error.message : "无法连接到大模型生成引擎后端服务，请检查服务状态。"}
            </p>
            <Button
              onClick={() => refetch()}
              className="bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-semibold shadow-md active:scale-95 transition-all"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              重试握手连接
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10">
      {/* 🚀 Hero Banner Section */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-950/40 via-purple-950/20 to-background border border-border/40 p-8 md:p-10 hover:shadow-[0_0_50px_oklch(0.68_0.19_285/0.08)] transition-all duration-500">
        <div className="absolute top-0 right-0 p-12 opacity-5 pointer-events-none">
          <BookOpen className="w-48 h-48 text-primary" />
        </div>
        <div className="max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 animate-pulse">
            ✨ 智能小说写作工坊
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            我的小说创作空间
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed max-w-xl">
            基于先进大语言模型的智能写作助手。在此管理您的所有创作项目，开启小说的大纲设计、正文草稿生成、多角色脑暴及平台化质检。
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <Button
              onClick={() => setCreateOpen(true)}
              className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none shadow-md shadow-indigo-600/10 hover:shadow-indigo-600/20 active:scale-95 transition-all rounded-xl font-semibold h-10 px-5"
            >
              <Plus className="h-4.5 w-4.5 mr-2" />
              新建创作项目
            </Button>
            <Button
            variant="outline"
            onClick={() => setConfigOpen(true)}
            className="rounded-xl border-border/60 hover:bg-accent/40 font-medium h-10 px-5"
          >
            配置全局模型节点
          </Button>
          <Button
            variant="outline"
            onClick={() => setMigrationOpen(true)}
            className="rounded-xl border-border/60 hover:bg-accent/40 font-medium h-10 px-5 text-muted-foreground hover:text-foreground"
          >
            旧数据迁移
          </Button>
          </div>
        </div>
      </div>

      {/* 📊 Sleek Metrics Summary Cards */}
      {projects && projects.length > 0 && (
        <ProjectStats stats={stats} />
      )}

      {/* 📚 Projects Grid */}
      {!projects?.length ? (
        <Card className="text-center py-16 glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all max-w-lg mx-auto rounded-3xl">
          <CardContent className="space-y-4 pt-6">
            <div className="h-16 w-16 mx-auto rounded-full bg-violet-500/10 flex items-center justify-center text-violet-400 border border-violet-500/20 mb-2">
              <BookOpen className="h-8 w-8" />
            </div>
            <h2 className="text-xl font-bold text-foreground">尚未创建任何项目</h2>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
              您的创作灵感从这里出发。创建一个小说创作项目，开启您的 AI 辅助写作之旅。
            </p>
            <Button
              onClick={() => setCreateOpen(true)}
              size="lg"
              className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none shadow-md shadow-indigo-600/10 rounded-xl font-semibold px-6 py-2.5 mt-2 active:scale-95 transition-all"
            >
              <Plus className="h-5 w-5 mr-2" />
              开始创作
            </Button>
          </CardContent>
        </Card>
      ) : filteredProjects?.length === 0 ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-sm text-muted-foreground">没有找到匹配 &quot;{searchQuery}&quot; 的小说项目</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.replace("/")}
            className="text-muted-foreground border-border/50 hover:text-foreground text-xs rounded-lg"
          >
            清除搜索条件
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects?.map((p: any) => (
            <ProjectCard
              key={p.id}
              project={p}
              onDelete={(id) => setDeleteTarget(id)}
            />
          ))}
        </div>
      )}

      {/* 🗑️ Delete Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <DialogContent className="max-w-sm bg-background/95 backdrop-blur-xl border-border/60 p-5 rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-destructive flex items-center gap-2">
              <Trash2 className="h-4 w-4" />
              确认删除该项目？
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground/80 mt-2 leading-relaxed">
              此操作不可撤销，将永久从算力底座中清除该项目的所有大纲配置、角色关系图谱、章节内容和调试数据。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex gap-2 justify-end">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs rounded-lg"
              onClick={() => setDeleteTarget(null)}
              disabled={deleteProject.isPending}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="h-8 text-xs rounded-lg font-semibold"
              onClick={handleDeleteConfirm}
              disabled={deleteProject.isPending}
            >
              {deleteProject.isPending ? "删除中..." : "确认永久删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Project Modal */}
      <CreateProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {/* Model Setup Modal */}
      <ModelConfigDialog
        open={configOpen}
        onOpenChange={setConfigOpen}
      />

      {/* Data Migration Modal */}
      <DataMigrationDialog
        open={migrationOpen}
        onOpenChange={setMigrationOpen}
      />
    </div>
  )
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="max-w-6xl mx-auto space-y-8 pb-10">
        <Skeleton className="h-[210px] w-full rounded-3xl bg-card/40 border border-border/40" />
      </div>
    }>
      <HomeContent />
    </Suspense>
  )
}
