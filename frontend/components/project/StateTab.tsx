"use client"

import React, { useEffect, useState } from "react"
import { useProjectContext } from "./ProjectContext"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api-client"
import { OutlineEvolutionPanel } from "./OutlineEvolutionPanel"
import { ConflictsTab } from "./state_tabs/ConflictsTab"
import { AuditTab } from "./state_tabs/AuditTab"
import { BackupsTab } from "./state_tabs/BackupsTab"
import { CharactersEditTab, NameRulesEditTab, PlotThreadsEditTab, GlobalSummaryEditTab } from "./state_tabs/StateEditorForms"
import { OutlineEditTab } from "./state_tabs/OutlineEditTab"
import { HelpGuideModal } from "./HelpGuideModal"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, AlertTriangle, CheckCircle, Info } from "lucide-react"

export function StateTab() {
  const { projectId } = useProjectContext()
  const [stateData, setStateData] = useState<any>(null)
  const [healthData, setHealthData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [stateRes, healthRes] = await Promise.all([
        api.client.get(`/api/v1/projects/${projectId}/state`),
        api.client.get(`/api/v1/projects/${projectId}/health`)
      ])
      setStateData(stateRes.data)
      setHealthData(healthRes.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleExportBible = async () => {
    try {
      const res = await api.client.get(`/api/v1/projects/${projectId}/export/story-bible`)
      const blob = new Blob([res.data], { type: "text/markdown" })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `story_bible_${projectId.slice(0,8)}.md`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      alert("导出失败")
    }
  }

  useEffect(() => {
    loadData()
  }, [projectId])

  if (loading) return <div className="p-4 text-muted-foreground text-sm">加载中...</div>

  // Extract health metrics
  const getCheckCount = (key: string) => {
    if (!healthData) return 0
    const check = healthData.checks.find((c: any) => c.key === key)
    if (!check) return 0
    const match = check.message.match(/\d+/)
    return match ? parseInt(match[0], 10) : 1
  }

  const pendingPatches = getCheckCount("pending_patches")
  const highRiskPatches = getCheckCount("high_risk_patches")
  const pendingDiffs = getCheckCount("pending_diffs")
  const highRiskConflicts = getCheckCount("high_risk_conflicts")

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden gap-4">
      
      {/* Top Header & Health Card */}
      <div className="flex flex-col gap-2 shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold flex items-center gap-2">
            状态系统控制台
          </h2>
          <div className="flex items-center gap-2">
            <HelpGuideModal />
            <Button variant="outline" size="sm" onClick={handleExportBible} className="gap-1">
              <Download className="h-4 w-4" /> 导出设定包
            </Button>
          </div>
        </div>
        
        {healthData && (
          <Card className={`border-l-4 ${healthData.status === 'healthy' ? 'border-l-green-500' : healthData.status === 'danger' || healthData.status === 'broken' ? 'border-l-red-500' : 'border-l-amber-500'}`}>
            <CardContent className="p-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-muted-foreground">健康等级:</span>
                {healthData.status === 'healthy' && <span className="text-green-600 flex items-center gap-1"><CheckCircle className="h-4 w-4"/> Healthy</span>}
                {healthData.status === 'warning' && <span className="text-amber-600 flex items-center gap-1"><Info className="h-4 w-4"/> Warning</span>}
                {(healthData.status === 'danger' || healthData.status === 'broken') && <span className="text-red-600 flex items-center gap-1"><AlertTriangle className="h-4 w-4"/> {healthData.status}</span>}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-muted-foreground">待处理 Patch:</span>
                <span className={highRiskPatches > 0 ? "text-red-600 font-bold" : pendingPatches > 0 ? "text-amber-600 font-bold" : ""}>
                  {pendingPatches + highRiskPatches} {highRiskPatches > 0 && `(${highRiskPatches} 高风险)`}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-muted-foreground">待处理大纲 Diff:</span>
                <span className={pendingDiffs > 0 ? "text-amber-600 font-bold" : ""}>{pendingDiffs}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-muted-foreground">高风险冲突:</span>
                <span className={highRiskConflicts > 0 ? "text-red-600 font-bold" : ""}>{highRiskConflicts}</span>
              </div>
              <div className="w-full text-xs text-muted-foreground mt-1">
                {healthData.summary}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Tabs defaultValue="overview" className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="mb-2 self-start flex-wrap h-auto">
          <TabsTrigger value="overview">总览与演化 {pendingPatches + highRiskPatches > 0 && `(${pendingPatches + highRiskPatches})`}</TabsTrigger>
          <TabsTrigger value="characters">人物状态</TabsTrigger>
          <TabsTrigger value="name_rules">称呼规则</TabsTrigger>
          <TabsTrigger value="plot_threads">伏笔状态</TabsTrigger>
          <TabsTrigger value="outline">大纲规划</TabsTrigger>
          <TabsTrigger value="global_summary">全局摘要</TabsTrigger>
          <TabsTrigger value="conflicts" className={highRiskConflicts > 0 ? "text-red-600" : "text-amber-600"}>冲突检测 {highRiskConflicts > 0 && `(${highRiskConflicts})`}</TabsTrigger>
          <TabsTrigger value="audit">审计日志</TabsTrigger>
          <TabsTrigger value="backups">备份与回滚</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="flex-1 flex flex-col overflow-hidden mt-0">
          <OutlineEvolutionPanel />
        </TabsContent>
        
        <TabsContent value="characters" className="flex-1 flex flex-col overflow-hidden mt-0">
          <CharactersEditTab stateData={stateData} loadData={loadData} />
        </TabsContent>
        
        <TabsContent value="name_rules" className="flex-1 flex flex-col overflow-hidden mt-0">
          <NameRulesEditTab stateData={stateData} loadData={loadData} />
        </TabsContent>
        
        <TabsContent value="plot_threads" className="flex-1 flex flex-col overflow-hidden mt-0">
          <PlotThreadsEditTab stateData={stateData} loadData={loadData} />
        </TabsContent>
        
        <TabsContent value="outline" className="flex-1 flex flex-col overflow-hidden mt-0">
          <OutlineEditTab stateData={stateData} loadData={loadData} />
        </TabsContent>
        
        <TabsContent value="global_summary" className="flex-1 flex flex-col overflow-hidden mt-0">
          <GlobalSummaryEditTab stateData={stateData} loadData={loadData} />
        </TabsContent>
        
        <TabsContent value="conflicts" className="flex-1 flex flex-col overflow-hidden mt-0">
          <ConflictsTab />
        </TabsContent>
        
        <TabsContent value="audit" className="flex-1 flex flex-col overflow-hidden mt-0">
          <AuditTab />
        </TabsContent>
        
        <TabsContent value="backups" className="flex-1 flex flex-col overflow-hidden mt-0">
          <BackupsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
