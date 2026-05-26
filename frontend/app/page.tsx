"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useProjects, useDeleteProject } from "@/lib/hooks/use-projects"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Plus, Trash2, BookOpen, Clock, CheckCircle } from "lucide-react"

export default function HomePage() {
  const router = useRouter()
  const { data: projects, isLoading } = useProjects()
  const deleteProject = useDeleteProject()
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const totalProjects = projects?.length || 0
  const readyProjects = projects?.filter((p: any) => p.status === "ready").length || 0
  const draftProjects = projects?.filter((p: any) => p.status === "draft").length || 0

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
            <Button onClick={() => router.push("/projects/new")} className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none shadow-md shadow-indigo-600/10 hover:shadow-indigo-600/20 active:scale-95 transition-all rounded-xl font-semibold">
              <Plus className="h-4.5 w-4.5 mr-2" />
              新建创作项目
            </Button>
            <Button variant="outline" onClick={() => router.push("/settings")} className="rounded-xl border-border/60 hover:bg-accent/40 font-medium">
              配置全局模型节点
            </Button>
          </div>
        </div>
      </div>

      {/* 📊 Sleek Metrics Summary Cards */}
      {totalProjects > 0 && !isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="glass-card border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.04)] transition-all duration-300">
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground font-semibold">项目总数</p>
                <h3 className="text-2xl font-bold mt-1 text-foreground">{totalProjects}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-violet-500/10 flex items-center justify-center text-violet-400 border border-violet-500/20">
                <BookOpen className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass-card border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.04)] transition-all duration-300">
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground font-semibold">已就绪空间</p>
                <h3 className="text-2xl font-bold mt-1 text-emerald-400">{readyProjects}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
                <CheckCircle className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.04)] transition-all duration-300">
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground font-semibold">草稿项目</p>
                <h3 className="text-2xl font-bold mt-1 text-amber-400">{draftProjects}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
                <Clock className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 📚 Projects List Section */}
      {isLoading ? (
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
      ) : !projects?.length ? (
        <Card className="text-center py-16 glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all max-w-lg mx-auto rounded-3xl">
          <CardContent className="space-y-4 pt-6">
            <div className="h-16 w-16 mx-auto rounded-full bg-violet-500/10 flex items-center justify-center text-violet-400 border border-violet-500/20 mb-2">
              <BookOpen className="h-8 w-8" />
            </div>
            <h2 className="text-xl font-bold text-foreground">尚未创建任何项目</h2>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
              您的创作灵感从这里出发。创建一个小说创作项目，开启您的 AI 辅助写作之旅。
            </p>
            <Button onClick={() => router.push("/projects/new")} size="lg" className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none shadow-md shadow-indigo-600/10 rounded-xl font-semibold px-6 py-2.5 mt-2 active:scale-95 transition-all">
              <Plus className="h-5 w-5 mr-2" />
              开始创作
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((p: any) => {
            const statusMap: Record<string, { label: string; style: string }> = {
              draft: { label: "草稿", style: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
              generating: { label: "生成中", style: "bg-primary/20 text-primary border-primary/30 animate-pulse" },
              ready: { label: "就绪", style: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
              archived: { label: "归档", style: "bg-secondary text-muted-foreground border-border" },
            }
            const statusKey = (p.status || "draft") as string
            const badgeConfig = statusMap[statusKey] || { label: statusKey, style: "bg-secondary text-muted-foreground" }

            return (
              <Card
                key={p.id}
                className="glass-card border-border/30 hover:scale-[1.01] hover:border-primary/40 hover:shadow-[0_0_25px_oklch(0.68_0.19_285/0.1)] transition-all duration-300 cursor-pointer flex flex-col justify-between h-[210px] p-5 relative group overflow-hidden"
                onClick={() => router.push(`/projects/${p.id}`)}
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors truncate flex-1">
                      {p.name}
                    </h3>
                    <Badge className={`text-[10px] shrink-0 font-semibold px-2 py-0 border ${badgeConfig.style}`}>
                      {badgeConfig.label}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed mt-1.5 h-[54px]">
                    {p.description || "暂无项目详情描述。点击进入详情，配置AI生成引擎。"}
                  </p>
                </div>

                <div className="flex items-center justify-between border-t border-border/20 pt-3">
                  <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3.5 w-3.5" />
                    {new Date(p.updated_at).toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" })}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(p.id) }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </Card>
            )
          })}
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
            <Button variant="outline" size="sm" className="h-8 text-xs rounded-lg" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="h-8 text-xs rounded-lg font-semibold"
              onClick={() => {
                if (deleteTarget) {
                  deleteProject.mutate(deleteTarget)
                  setDeleteTarget(null)
                }
              }}
            >
              确认永久删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

