"use client"

import { useParams, useRouter } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { PLATFORM_CONFIG } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { AlertCircle } from "lucide-react"

import ProjectLoading from "./loading"
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
import { PromptsTab } from "@/components/project/PromptsTab"
import { AnalyticsTab } from "@/components/project/AnalyticsTab"
import { PlotArcsTab } from "@/components/project/PlotArcsTab"
import { GraphTab } from "@/components/project/GraphTab"

function ProjectDashboardContent() {
  const { project, config, activeTab, setActiveTab } = useProjectContext()

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between mb-6 shrink-0">
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

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0 gap-6">
        <TabsList className="flex flex-wrap p-1 gap-1 bg-muted/60 backdrop-blur-md rounded-xl w-fit shrink-0">
          <TabsTrigger value="overview" className="rounded-lg px-4 py-2 text-sm">概览</TabsTrigger>
          <TabsTrigger value="workbench" className="rounded-lg px-4 py-2 text-sm">章节工作台</TabsTrigger>
          <TabsTrigger value="generation" className="rounded-lg px-4 py-2 text-sm">AI 生成</TabsTrigger>
          <TabsTrigger value="files" className="rounded-lg px-4 py-2 text-sm">文件输出</TabsTrigger>
          <TabsTrigger value="knowledge" className="rounded-lg px-4 py-2 text-sm">知识库</TabsTrigger>
          <TabsTrigger value="graph" className="rounded-lg px-4 py-2 text-sm">知识图谱</TabsTrigger>
          <TabsTrigger value="characters" className="rounded-lg px-4 py-2 text-sm">人物规划</TabsTrigger>
          <TabsTrigger value="plotarcs" className="rounded-lg px-4 py-2 text-sm">伏笔暗线</TabsTrigger>
          <TabsTrigger value="pipeline" className="rounded-lg px-4 py-2 text-sm">素材加工站</TabsTrigger>
          <TabsTrigger value="reader" className="rounded-lg px-4 py-2 text-sm">读者反馈</TabsTrigger>
          <TabsTrigger value="platform" className="rounded-lg px-4 py-2 text-sm">
            {PLATFORM_CONFIG[config?.platform]?.icon || "📖"} {PLATFORM_CONFIG[config?.platform]?.label || "平台"}工具
          </TabsTrigger>
          <TabsTrigger value="prompts" className="rounded-lg px-4 py-2 text-sm font-semibold text-purple-400">提示词实验</TabsTrigger>
          <TabsTrigger value="analytics" className="rounded-lg px-4 py-2 text-sm">分析统计</TabsTrigger>
          <TabsTrigger value="settings" className="rounded-lg px-4 py-2 text-sm">参数设置</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-0 outline-none">
          <OverviewTab />
        </TabsContent>

        <TabsContent value="workbench" className="mt-0 outline-none flex-1 min-h-0 flex flex-col">
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
        
        <TabsContent value="graph" className="mt-0 outline-none">
          <GraphTab />
        </TabsContent>

        <TabsContent value="characters" className="mt-0 outline-none">
          <CharactersTab id={project.id} />
        </TabsContent>
        
        <TabsContent value="plotarcs" className="mt-0 outline-none">
          <PlotArcsTab />
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

        <TabsContent value="prompts" className="mt-0 outline-none">
          <PromptsTab />
        </TabsContent>

        <TabsContent value="analytics" className="mt-0 outline-none">
          <AnalyticsTab />
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
    return <ProjectLoading />
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
