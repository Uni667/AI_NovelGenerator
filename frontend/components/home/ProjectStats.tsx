"use client"

import { Card, CardContent } from "@/components/ui/card"
import { BookOpen, CheckCircle, Clock } from "lucide-react"
import { ProjectStats as StatsType } from "@/lib/services/projectService"

interface ProjectStatsProps {
  stats: StatsType
}

export function ProjectStats({ stats }: ProjectStatsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Card className="glass-card border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.04)] transition-all duration-300">
        <CardContent className="p-5 flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground font-semibold">项目总数</p>
            <h3 className="text-2xl font-bold mt-1 text-foreground">{stats.total}</h3>
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
            <h3 className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">{stats.ready}</h3>
          </div>
          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle className="h-5 w-5" />
          </div>
        </CardContent>
      </Card>

      <Card className="glass-card border-border/40 hover:shadow-[0_0_20px_oklch(0.68_0.19_285/0.04)] transition-all duration-300">
        <CardContent className="p-5 flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground font-semibold">草稿项目</p>
            <h3 className="text-2xl font-bold mt-1 text-amber-600 dark:text-amber-400">{stats.draft}</h3>
          </div>
          <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Clock className="h-5 w-5" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
