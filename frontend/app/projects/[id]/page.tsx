"use client"

import { useParams, useRouter } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { PLATFORM_CONFIG } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { AlertCircle, ChevronDown, ChevronUp } from "lucide-react"
import { useState } from "react"

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
import { StateTab } from "@/components/project/StateTab"
import { SettingsTab } from "@/components/project/SettingsTab"
import { MaterialPipelineTab } from "@/components/project/MaterialPipelineTab"
import { PromptsTab } from "@/components/project/PromptsTab"
import { AnalyticsTab } from "@/components/project/AnalyticsTab"
import { PlotArcsTab } from "@/components/project/PlotArcsTab"
import { GraphTab } from "@/components/project/GraphTab"
import { VisualizerTab } from "@/components/project/VisualizerTab"
import { EmotionTab } from "@/components/project/EmotionTab"

function ProjectDashboardContent() {
  const { project, config, activeTab, setActiveTab } = useProjectContext()
  const [showMoreTabs, setShowMoreTabs] = useState(false)
  const router = useRouter()

  const moreTabs = [
    { value: "characters", label: "人物规划" },
    { value: "plotarcs", label: "伏笔暗线" },
    { value: "pipeline", label: "素材加工站" },
    { value: "reader", label: "读者反馈" },
    { value: "platform", label: (PLATFORM_CONFIG[config?.platform]?.icon || "📖") + " " + (PLATFORM_CONFIG[config?.platform]?.label || "平台") + "工具" },
    { value: "emotion", label: "🎭 情感分析" },
    { value: "prompts", label: "提示词实验", className: "font-semibold text-purple-400" },
    { value: "analytics", label: "API 使用情况" },
    { value: "settings", label: "参数设置" },
  ] as const

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 shrink-0">
        <div className="min-w-0">
          <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent truncate">
            {project.name}
          </h1>
          <p className="text-muted-foreground text-xs md:text-sm mt-0.5 truncate">{project.description || "暂无简介"}</p>
        </div>
        <Badge variant={project.status === "ready" ? "default" : "secondary"} className="text-xs px-3 py-1 w-fit">
          {project.status === "draft" ? "草稿" : project.status === "ready" ? "就绪" : project.status}
        </Badge>
      </div>

      <Tabs 
        value={activeTab} 
        onValueChange={setActiveTab} 
        className="flex-1 flex flex-col min-h-0 gap-6"
      >
        <TabsList className="flex flex-nowrap overflow-x-auto max-w-full md:flex-wrap p-1 gap-1 bg-muted/60 backdrop-blur-md rounded-xl w-full shrink-0 scrollbar-none">
          <TabsTrigger value="overview" className="rounded-lg px-4 py-2 text-sm shrink-0">概览</TabsTrigger>
          <TabsTrigger value="workbench" className="rounded-lg px-4 py-2 text-sm shrink-0">章节工作台</TabsTrigger>
          <TabsTrigger value="generation" className="rounded-lg px-4 py-2 text-sm shrink-0">AI 生成</TabsTrigger>
          <TabsTrigger value="files" className="rounded-lg px-4 py-2 text-sm shrink-0">文件输出</TabsTrigger>
          <TabsTrigger value="knowledge" className="rounded-lg px-4 py-2 text-sm shrink-0">知识库</TabsTrigger>
          <TabsTrigger value="graph" className="rounded-lg px-4 py-2 text-sm shrink-0">知识图谱</TabsTrigger>
          <TabsTrigger value="visualizer" className="rounded-lg px-4 py-2 text-sm shrink-0">小说可视化</TabsTrigger>
          {/* 更多按钮 — 展开低频 tab */}
          <button
            type="button"
            onClick={() => setShowMoreTabs(!showMoreTabs)}
            className={`inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm shrink-0 transition-colors ${
              showMoreTabs || moreTabs.some(t => t.value === activeTab)
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {showMoreTabs ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            更多
          </button>
          {showMoreTabs && moreTabs.map(tab => (
            <TabsTrigger key={tab.value} value={tab.value} className="rounded-lg px-3 py-2 text-sm shrink-0">
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview" className="mt-0 outline-none">
          <OverviewTab />
        </TabsContent>

        <TabsContent value="state" className="mt-0 outline-none min-h-0 flex-1">
          <StateTab />
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

        <TabsContent value="visualizer" className="mt-0 outline-none">
          <VisualizerTab />
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

        <TabsContent value="emotion" className="mt-0 outline-none">
          <EmotionTab />
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
