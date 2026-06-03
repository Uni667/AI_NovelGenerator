"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Trash2, Clock, BookMarked } from "lucide-react"
import { Project } from "@/lib/types"
import { useRouter } from "next/navigation"

interface ProjectCardProps {
  project: Project
  onDelete: (id: string, e: React.MouseEvent) => void
}

const statusMap: Record<string, { label: string; style: string }> = {
  draft: { label: "草稿", style: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20" },
  generating: { label: "生成中", style: "bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border-indigo-500/30 animate-pulse" },
  ready: { label: "就绪", style: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" },
  completed: { label: "已完成", style: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20" },
  failed: { label: "异常", style: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20" },
  error: { label: "异常", style: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20" },
  archived: { label: "归档", style: "bg-secondary text-muted-foreground border-border" },
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const router = useRouter()
  const statusKey = project.status || "draft"
  const badgeConfig = statusMap[statusKey] || { label: statusKey, style: "bg-secondary text-muted-foreground" }
  
  const updateDate = project.updated_at
    ? new Date(project.updated_at).toLocaleDateString("zh-CN", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "暂无更新"

  const platformLabelMap: Record<string, string> = {
    tomato: "番茄",
    qidian: "起点",
    jjwxc: "晋江",
    short_drama: "短剧",
    other: "自定义"
  }
  const displayPlatform = project.platform ? (platformLabelMap[project.platform] || "平台") : ""
  const displayGenre = project.genre || ""
  
  const subtitle = displayGenre && displayPlatform 
    ? `${displayGenre} · ${displayPlatform}`
    : displayGenre || displayPlatform || ""

  return (
    <Card
      className="glass-card border-border/30 hover:scale-[1.01] hover:border-primary/40 hover:shadow-[0_0_25px_oklch(0.68_0.19_285/0.1)] transition-all duration-300 cursor-pointer flex flex-col justify-between h-[210px] p-5 relative group overflow-hidden"
      onClick={() => router.push(`/projects/${project.id}`)}
    >
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors truncate flex-1">
            {project.name}
          </h3>
          <Badge className={`text-[10px] shrink-0 font-semibold px-2 py-0 border ${badgeConfig.style}`}>
            {badgeConfig.label}
          </Badge>
        </div>
        
        {subtitle && (
          <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/15">
            <BookMarked className="h-3 w-3" />
            {subtitle}
          </span>
        )}
        
        <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed mt-1.5 h-[54px]">
          {project.description || "暂无项目详情描述。点击进入工作台，配置AI写作引擎。"}
        </p>
      </div>

      <div className="flex items-center justify-between border-t border-border/20 pt-3">
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          {updateDate}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
          onClick={(e) => {
            e.stopPropagation()
            onDelete(project.id, e)
          }}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  )
}
