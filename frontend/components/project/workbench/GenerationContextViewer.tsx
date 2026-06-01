"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Eye, Loader2, AlertTriangle, Info } from "lucide-react"
import { useProjectContext } from "../ProjectContext"
import { toast } from "sonner"

export function GenerationContextViewer() {
  const { projectId, workbench: { selectedChapterNumber } } = useProjectContext()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [contextData, setContextData] = useState<any>(null)

  const fetchContext = async () => {
    try {
      setLoading(true)
      const res = await fetch(`/api/v1/projects/${projectId}/chapters/${selectedChapterNumber}/generation-context`)
      if (!res.ok) throw new Error("获取生成上下文失败")
      const data = await res.json()
      setContextData(data)
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(val) => {
      setOpen(val)
      if (val) fetchContext()
    }}>
      <DialogTrigger render={<Button variant="outline" className="bg-card/40 border-border/80" />}>
        <Eye className="h-4 w-4 mr-2 text-indigo-400" />查看本章上下文
      </DialogTrigger>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col overflow-hidden bg-background/95 backdrop-blur-xl border-white/10">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            第 {selectedChapterNumber} 章 生成上下文预览
          </DialogTitle>
          <DialogDescription>
            展示大模型生成本章时将要读取的状态摘要。已排除未合并的 Pending Patches。
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : contextData ? (
          <ScrollArea className="flex-1 pr-4">
            <div className="space-y-6 pb-6">
              {/* 状态总览 */}
              <div className="flex flex-col gap-2 p-4 rounded-lg bg-card border border-white/5">
                <div className="flex items-center gap-2 text-sm">
                  <span className={`px-2 py-1 rounded text-xs ${contextData.has_memory_state ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                    {contextData.has_memory_state ? "Memory State 已接入" : "未接入 Memory State (旧逻辑降级)"}
                  </span>
                  <span className="px-2 py-1 rounded text-xs bg-blue-500/20 text-blue-400">
                    已合并状态: {contextData.used_merged_state_only ? "仅读取" : "否"}
                  </span>
                  {contextData.pending_patch_ignored_count > 0 && (
                    <span className="px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-400">
                      已隔离 Pending Patch: {contextData.pending_patch_ignored_count}
                    </span>
                  )}
                </div>
                {contextData.context_warnings?.length > 0 && (
                  <div className="mt-2 text-sm text-yellow-400 flex flex-col gap-1">
                    {contextData.context_warnings.map((w: string, i: number) => (
                      <div key={i} className="flex items-center gap-2"><AlertTriangle className="h-4 w-4" />{w}</div>
                    ))}
                  </div>
                )}
              </div>

              {/* 细节区块 */}
              {contextData.has_memory_state && (
                <>
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-rose-400 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" /> 不可违背事实 & 禁止事项
                    </h3>
                    <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/20 text-sm whitespace-pre-wrap">
                      {(contextData.context?.locked_previous_facts?.length > 0 || contextData.context?.forbidden_violations?.length > 0) ? 
                        [...(contextData.context?.locked_previous_facts || []), ...(contextData.context?.forbidden_violations || [])].join("\\n") 
                        : "无"
                      }
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
                      <Info className="h-4 w-4" /> 称呼规则限制
                    </h3>
                    <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/20 text-sm whitespace-pre-wrap">
                      {contextData.context?.name_usage_rules_brief || "暂无规则"}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                      <Info className="h-4 w-4" /> 人物核心状态
                    </h3>
                    <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-sm whitespace-pre-wrap">
                      {contextData.context?.character_state_brief || "暂无人物状态"}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-purple-400 flex items-center gap-2">
                      <Info className="h-4 w-4" /> 伏笔与秘密
                    </h3>
                    <div className="p-3 rounded-md bg-purple-500/10 border border-purple-500/20 text-sm whitespace-pre-wrap">
                      {contextData.context?.plot_threads_brief || "暂无活跃伏笔"}
                    </div>
                  </div>
                </>
              )}
            </div>
          </ScrollArea>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
