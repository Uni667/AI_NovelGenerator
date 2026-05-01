"use client"

import { useRouter } from "next/navigation"
import { useProjects, useDeleteProject } from "@/lib/hooks/use-projects"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Plus, Trash2, BookOpen, Clock } from "lucide-react"

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  draft: { label: "草稿", variant: "secondary" },
  generating: { label: "生成中", variant: "default" },
  ready: { label: "就绪", variant: "default" },
  archived: { label: "归档", variant: "outline" },
}

export default function HomePage() {
  const router = useRouter()
  const { data: projects, isLoading } = useProjects()
  const deleteProject = useDeleteProject()

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">我的小说项目</h1>
          <p className="text-muted-foreground mt-1">使用 AI 辅助创作你的下一部小说</p>
        </div>
        <Button onClick={() => router.push("/projects/new")} size="lg">
          <Plus className="h-5 w-5 mr-2" />新建项目
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">加载中...</div>
      ) : !projects?.length ? (
        <Card className="text-center py-16">
          <CardContent>
            <BookOpen className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">还没有项目</h2>
            <p className="text-muted-foreground mb-4">创建你的第一个小说项目，开始 AI 辅助写作之旅</p>
            <Button onClick={() => router.push("/projects/new")} size="lg">
              <Plus className="h-5 w-5 mr-2" />开始创作
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {projects.map((p: any) => (
            <Card key={p.id} className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => router.push(`/projects/${p.id}`)}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{p.name}</CardTitle>
                    {p.description && <CardDescription>{p.description}</CardDescription>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={statusMap[p.status]?.variant || "secondary"}>
                      {statusMap[p.status]?.label || p.status}
                    </Badge>
                    <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); deleteProject.mutate(p.id) }}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <span className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Clock className="h-3 w-3" />{new Date(p.updated_at).toLocaleDateString("zh-CN")}
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
