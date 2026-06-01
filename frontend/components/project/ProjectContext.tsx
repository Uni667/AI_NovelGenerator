"use client"

import React, { createContext, useContext, ReactNode, useState, useRef, useEffect } from "react"
import { useGenerationState } from "@/lib/hooks/use-generation-state"
import { useWorkbenchState } from "@/lib/hooks/use-workbench-state"
import { usePlatformTools } from "@/lib/hooks/use-platform-tools"
import { useProject, useProjectConfig, useChapters, useUpdateProjectConfig } from "@/lib/hooks/use-projects"
import { useSearchParams, useRouter } from "next/navigation"

export type ProjectContextType = {
  projectId: string;
  project: any; // ReturnType<typeof useProject>['data']
  config: any;
  chapters: any[];
  refetchChapters: () => void;
  updateConfig: ReturnType<typeof useUpdateProjectConfig>;
  generation: ReturnType<typeof useGenerationState>;
  workbench: ReturnType<typeof useWorkbenchState>;
  platform: ReturnType<typeof usePlatformTools>;
  
  // Shared state that doesn't fit well in specific hooks
  batchUploading: boolean;
  setBatchUploading: (val: boolean) => void;
  batchFileRef: React.RefObject<HTMLInputElement | null>;
  activeTab: string;
  setActiveTab: (val: string) => void;
  selectedOutputFile: string;
  setSelectedOutputFile: (val: string) => void;
};

const ProjectContext = createContext<ProjectContextType | null>(null)

export function ProjectProvider({ projectId, children }: { projectId: string; children: ReactNode }) {
  const { data: project } = useProject(projectId)
  const { data: config } = useProjectConfig(projectId)
  const { data: chapters, refetch: refetchChapters } = useChapters(projectId)
  const updateConfig = useUpdateProjectConfig(projectId)
  
  const generation = useGenerationState(projectId)
  const workbench = useWorkbenchState(projectId)
  const platform = usePlatformTools(projectId)

  const [batchUploading, setBatchUploading] = useState(false)
  const batchFileRef = useRef<HTMLInputElement | null>(null)
  
  const router = useRouter()
  const searchParams = useSearchParams()
  const tabParam = searchParams?.get('tab')
  
  const [activeTab, setActiveTabState] = useState(() => {
    // 支持从 URL 参数读取初始 tab（例如侧栏点击 API 使用情况）
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const tabParam = params.get('tab')
      if (tabParam) return tabParam
    }
    return "overview"
  })

  const setActiveTab = React.useCallback((val: string) => {
    setActiveTabState(val)
    router.push(`/projects/${projectId}?tab=${val}`)
  }, [projectId, router])

  useEffect(() => {
    if (tabParam && tabParam !== activeTab) {
      setActiveTabState(tabParam)
    }
  }, [tabParam, activeTab])

  const [selectedOutputFile, setSelectedOutputFile] = useState("Novel_architecture.txt")

  const value: ProjectContextType = {
    projectId,
    project,
    config,
    chapters: chapters || [],
    refetchChapters,
    updateConfig,
    generation,
    workbench,
    platform,
    batchUploading,
    setBatchUploading,
    batchFileRef,
    activeTab,
    setActiveTab,
    selectedOutputFile,
    setSelectedOutputFile
  }

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
}

export function useProjectContext() {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error("useProjectContext must be used within a ProjectProvider")
  }
  return context
}
