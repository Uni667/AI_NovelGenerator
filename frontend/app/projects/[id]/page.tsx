"use client"

import { useParams, useRouter } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { PLATFORM_CONFIG } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle } from "lucide-react"

import { ProjectProvider, useProjectContext } from "@/components/project/ProjectContext"

// Import modular tab components
import { OverviewTab } from "@/components/project/OverviewTab"
import { WorkbenchTab } from "@/components/project/WorkbenchTab"
import { GenerationTab } from "@/components/project/GenerationTab"
import { FilesTab } from "@/components/project/FilesTab"
import { KnowledgeTab } from "@/components/project/KnowledgeTab"
import { CharactersTab } from "@/components/project/CharactersTab"
import { ReaderTab } from "@/components/project/ReaderTab"
import { PlatformToolsTab } from "@/components/project/PlatformToolsTab"
import { SettingsTab } from "@/components/project/SettingsTab"
import { MaterialPipelineTab } from "@/components/project/MaterialPipelineTab"

function ProjectDashboardContent() {
  const router = useRouter()
  const { project, config, activeTab, setActiveTab } = useProjectContext()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
            {project.name}
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">{project.description || "暂无简介"}</p>
        </div>
        <Badge variant={project.status === "ready" ? "default" : "secondary"} className="text-xs px-3 py-1">
          {project.status === "draft" ? "草稿" : project.status === "ready" ? "就绪" : project.status}
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="flex flex-wrap p-1 gap-1 bg-muted/60 backdrop-blur-md rounded-xl w-fit">
          <TabsTrigger value="overview" className="rounded-lg px-4 py-2 text-sm">概览</TabsTrigger>
          <TabsTrigger value="workbench" className="rounded-lg px-4 py-2 text-sm">章节工作台</TabsTrigger>
          <TabsTrigger value="generation" className="rounded-lg px-4 py-2 text-sm">AI 生成</TabsTrigger>
          <TabsTrigger value="files" className="rounded-lg px-4 py-2 text-sm">文件输出</TabsTrigger>
          <TabsTrigger value="knowledge" className="rounded-lg px-4 py-2 text-sm">知识库</TabsTrigger>
          <TabsTrigger value="characters" className="rounded-lg px-4 py-2 text-sm">人物规划</TabsTrigger>
          <TabsTrigger value="pipeline" className="rounded-lg px-4 py-2 text-sm">素材加工站</TabsTrigger>
          <TabsTrigger value="reader" className="rounded-lg px-4 py-2 text-sm">读者反馈</TabsTrigger>
          <TabsTrigger value="platform" className="rounded-lg px-4 py-2 text-sm">
            {PLATFORM_CONFIG[config?.platform]?.icon || "📖"} {PLATFORM_CONFIG[config?.platform]?.label || "平台"}工具
          </TabsTrigger>
          <TabsTrigger value="settings" className="rounded-lg px-4 py-2 text-sm">参数设置</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-0 outline-none">
          <OverviewTab />
        </TabsContent>

        <TabsContent value="workbench" className="mt-0 outline-none">
          <WorkbenchTab />
        </TabsContent>

        <TabsContent value="generation" className="mt-0 outline-none">
          <GenerationTab />
        </TabsContent>

        <TabsContent value="files" className="mt-0 outline-none">
          <FilesTab />
        </TabsContent>

        <TabsContent value="knowledge" className="mt-0 outline-none">
          <KnowledgeTab />
        </TabsContent>

        <TabsContent value="characters" className="mt-0 outline-none">
          <CharactersTab id={project.id} />
        </TabsContent>

        <TabsContent value="pipeline" className="mt-0 outline-none">
          <MaterialPipelineTab />
        </TabsContent>

        <TabsContent value="reader" className="mt-0 outline-none">
          <ReaderTab />
        </TabsContent>

        <TabsContent value="platform" className="mt-0 outline-none">
          <PlatformToolsTab />
        </TabsContent>

        <TabsContent value="settings" className="mt-0 outline-none">
          <SettingsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default function ProjectDashboard() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { data: project, isLoading, error: projectError } = useProject(id)

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
        <Skeleton className="h-10 w-full max-w-md" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (projectError || !project) {
    return (
      <div className="mx-auto max-w-xl rounded-lg border p-6 text-center">
        <AlertCircle className="mx-auto mb-3 h-8 w-8 text-destructive" />
        <h1 className="text-lg font-semibold">项目不存在或你没有权限访问。</h1>
        <p className="mt-2 text-sm text-muted-foreground">请确认当前登录账号，或返回项目列表重新选择。</p>
        <Button className="mt-4" onClick={() => router.push("/")}>返回项目列表</Button>
      </div>
    )
  }

  return (
    <ProjectProvider projectId={id}>
      <ProjectDashboardContent />
    </ProjectProvider>
  )
}
