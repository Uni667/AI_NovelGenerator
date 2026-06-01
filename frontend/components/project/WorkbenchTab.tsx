"use client"
 
import React from "react"
import { WorkbenchSidebar } from "./workbench/WorkbenchSidebar"
import { WorkbenchEditor } from "./workbench/WorkbenchEditor"
import { WorkbenchStatusPane } from "./workbench/WorkbenchStatusPane"
import { useProjectContext } from "./ProjectContext"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { Sparkles, AlertCircle, CheckCircle2 } from "lucide-react"
import { api } from "@/lib/api-client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
 
export function WorkbenchTab() {
  const {
    layoutMode, setLayoutMode,
    leftPanelCollapsed, setLeftPanelCollapsed,
    rightPanelCollapsed, setRightPanelCollapsed,
    leftDrawerOpen, setLeftDrawerOpen,
    assistantDrawerOpen, setAssistantDrawerOpen
  } = useProjectContext().workbench
  const { projectId } = useProjectContext()

  const [healthData, setHealthData] = React.useState<any>(null)

  React.useEffect(() => {
    if (!projectId) return
    api.client.get(`/api/v1/projects/${projectId}/health`)
      .then(res => setHealthData(res.data))
      .catch(console.error)
  }, [projectId])

  // Handle responsive screens automatically
  React.useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      const savedUserSelect = localStorage.getItem("ai-novel-workbench-layout-mode-user-select")
      
      if (width < 900) {
        setLayoutMode("focus")
      } else if (width < 1200) {
        if (!savedUserSelect || savedUserSelect === "standard") {
          setLayoutMode("wide")
        } else {
          setLayoutMode(savedUserSelect as 'standard' | 'wide' | 'focus')
        }
      } else if (width < 1440) {
        if (!savedUserSelect || savedUserSelect === "standard") {
          setLayoutMode("wide")
        } else {
          setLayoutMode(savedUserSelect as 'standard' | 'wide' | 'focus')
        }
      } else {
        if (savedUserSelect) {
          setLayoutMode(savedUserSelect as 'standard' | 'wide' | 'focus')
        } else {
          setLayoutMode("standard")
        }
      }
    }

    window.addEventListener("resize", handleResize)
    handleResize() // Run on mount
    return () => window.removeEventListener("resize", handleResize)
  }, [setLayoutMode])

  // Determine grid template columns
  let gridColumns = "300px minmax(560px, 1fr) 340px"
  if (layoutMode === "focus") {
    gridColumns = "minmax(0, 1fr)"
  } else if (layoutMode === "wide") {
    gridColumns = "48px minmax(720px, 1fr) 56px"
  } else {
    // Standard layout: respects manual panel collapse toggling
    const leftW = leftPanelCollapsed ? "48px" : "300px"
    const rightW = rightPanelCollapsed ? "56px" : "340px"
    gridColumns = `${leftW} minmax(560px, 1fr) ${rightW}`
  }
 
  return (
    <div
      className="flex-1 min-h-0 flex flex-col gap-4 xl:grid xl:gap-4 xl:transition-all xl:duration-300 relative"
      style={{
        gridTemplateColumns: gridColumns,
      }}
    >
      {/* Top Banner for Memory Context & Patches */}
      {healthData && (
        <div className="col-span-full">
          {(healthData.status === 'danger' || healthData.status === 'broken') ? (
            <Alert variant="destructive" className="bg-destructive/10 border-destructive text-destructive-foreground">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>高风险状态</AlertTitle>
              <AlertDescription className="flex items-center justify-between">
                <span>{healthData.summary} (请进入状态页审查补丁或冲突)</span>
              </AlertDescription>
            </Alert>
          ) : (
            <Alert className="bg-muted border-border">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertTitle className="text-foreground">记忆上下文已接入</AlertTitle>
              <AlertDescription className="text-muted-foreground flex items-center justify-between">
                <span>生成引擎正在读取最新的全局摘要与人物设定。</span>
                {healthData.checks.find((c: any) => c.key === 'pending_patches' || c.key === 'high_risk_patches') && (
                  <span className="text-amber-500">提示: 存在未处理的 State Patch，请及时合并。</span>
                )}
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {/* Left Sidebar Chapter List / Collapsed Rail */}
      {layoutMode !== "focus" && (
        <div className="xl:min-h-0 shrink-0 overflow-hidden transition-all duration-300">
          <WorkbenchSidebar />
        </div>
      )}
 
      {/* Editor Center Area */}
      <div className="xl:min-h-0 flex-1 min-w-0 flex flex-col items-center">
        <div className="w-full h-full flex flex-col" style={{ maxWidth: layoutMode === "focus" ? "1280px" : "100%" }}>
          <WorkbenchEditor />
        </div>
      </div>
 
      {/* Right Assistant Panel / Collapsed Tool Rail */}
      {layoutMode !== "focus" && (
        <div className="xl:min-h-0 shrink-0 overflow-hidden transition-all duration-300">
          <WorkbenchStatusPane />
        </div>
      )}

      {/* Drawer for Left Directory Overlay in Wide/Focus mode */}
      <Sheet open={leftDrawerOpen} onOpenChange={setLeftDrawerOpen}>
        <SheetContent side="left" className="w-[320px] p-0 border-r border-border bg-[#05070d] flex flex-col">
          <div className="flex-1 min-h-0 p-4">
            <WorkbenchSidebar isDrawer />
          </div>
        </SheetContent>
      </Sheet>

      {/* Drawer for Right Assistant Overlay in Wide/Focus mode */}
      <Sheet open={assistantDrawerOpen} onOpenChange={setAssistantDrawerOpen}>
        <SheetContent side="right" className="w-[360px] p-0 border-l border-border bg-[#05070d] flex flex-col">
          <div className="flex-1 min-h-0 p-4">
            <WorkbenchStatusPane isDrawer />
          </div>
        </SheetContent>
      </Sheet>

      {/* Focus mode right floating AI assistant button */}
      {layoutMode === "focus" && (
        <button
          type="button"
          onClick={() => setAssistantDrawerOpen(true)}
          className="fixed right-6 bottom-20 z-40 h-10 w-10 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 hover:scale-105 transition-all duration-300 border border-white/10"
          title="打开 AI 助手"
        >
          <Sparkles className="h-5 w-5" />
        </button>
      )}
    </div>
  )
}
