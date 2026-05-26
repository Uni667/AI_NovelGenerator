"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Network } from "lucide-react"
import { GraphViewer } from "./workbench/GraphViewer"

export function GraphTab() {
  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 h-[85vh] flex flex-col">
        <CardHeader className="pb-4 shrink-0">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <Network className="h-5 w-5 text-primary" />
            人物关系与知识图谱 (Graph RAG)
          </CardTitle>
          <CardDescription>
            直观展示小说内的角色关系、势力分布与核心线索。生成章节时，AI 将自动检索相关的图谱节点以保持设定一致性。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 pb-6 px-6">
          <div className="h-full w-full rounded-xl border border-border/50 overflow-hidden bg-background/50 relative">
            <GraphViewer />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
