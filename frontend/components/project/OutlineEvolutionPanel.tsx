"use client"

import React, { useEffect, useState } from "react"
import { useProjectContext } from "./ProjectContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { AlertTriangle, Clock, Play, FileText, ArrowRight, Lock, BookOpen } from "lucide-react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export function OutlineEvolutionPanel() {
  const { projectId } = useProjectContext()
  const [outlineState, setOutlineState] = useState<any>(null)
  const [diffs, setDiffs] = useState<any[]>([])
  const [patches, setPatches] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [evolving, setEvolving] = useState(false)
  
  const [selectedDiff, setSelectedDiff] = useState<any>(null)
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false)

  const [selectedPatch, setSelectedPatch] = useState<any>(null)
  const [isPatchModalOpen, setIsPatchModalOpen] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const stateRes = await api.client.get(`/api/v1/projects/${projectId}/state`)
      setOutlineState(stateRes.data?.outline_state || { chapters: [] })
      const diffsRes = await api.client.get(`/api/v1/projects/${projectId}/outline/diffs`)
      setDiffs(diffsRes.data || [])
      const patchesRes = await api.client.get(`/api/v1/projects/${projectId}/state/patches`)
      setPatches(patchesRes.data?.patches || [])
    } catch (err) {
      toast.error("加载大纲及状态补丁数据失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [projectId])

  const handleEvolve = async () => {
    setEvolving(true)
    try {
      const res = await api.client.post(`/api/v1/projects/${projectId}/outline/evolve`, {
        from_chapter: 1,
        scope: "future_only",
        reason: "根据已定稿剧情调整后续规划"
      })
      if (res.data.success) {
        toast.success("生成大纲调整建议成功")
      } else {
        toast.error("生成大纲调整建议失败，已被拦截")
      }
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "生成失败")
    } finally {
      setEvolving(false)
    }
  }

  const handleApply = async (diffId: string) => {
    if (!confirm("确认应用此大纲调整吗？系统将备份当前大纲并进行增量修改。")) return;
    try {
      await api.client.post(`/api/v1/projects/${projectId}/outline/diffs/${diffId}/apply`)
      toast.success("大纲调整应用成功")
      setIsDiffModalOpen(false)
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "应用失败")
    }
  }

  const handleDiscard = async (diffId: string) => {
    if (!confirm("确定要放弃此建议吗？")) return;
    try {
      await api.client.post(`/api/v1/projects/${projectId}/outline/diffs/${diffId}/discard`)
      toast.success("建议已放弃")
      setIsDiffModalOpen(false)
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "放弃失败")
    }
  }

  const handleMergePatch = async (patchId: string) => {
    try {
      await api.client.post(`/api/v1/projects/${projectId}/state/patches/${patchId}/merge`)
      toast.success("补丁合并成功")
      setIsPatchModalOpen(false)
      loadData()
      if (typeof window !== "undefined") {
         window.location.reload()
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "合并失败")
    }
  }

  const handleDiscardPatch = async (patchId: string) => {
    if (!confirm("确定要废弃此状态补丁吗？这将不会更新人物设定和全局摘要。")) return;
    try {
      await api.client.post(`/api/v1/projects/${projectId}/state/patches/${patchId}/discard`)
      toast.success("补丁已废弃")
      setIsPatchModalOpen(false)
      loadData()
      if (typeof window !== "undefined") {
         window.location.reload()
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "废弃失败")
    }
  }

  const activePatches = patches.filter((p: any) => p.status === 'pending_review' || p.status === 'failed')

  return (
    <div className="flex-1 flex flex-col md:flex-row gap-4 overflow-hidden">
      {/* 左侧：当前大纲展示 */}
      <div className="flex-1 flex flex-col gap-4 overflow-y-auto">
        <Card className="border-border/50 shadow-sm flex-1 flex flex-col overflow-hidden">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">大纲状态 (Outline State)</CardTitle>
              <CardDescription>当前系统中的大纲快照，包含定稿锁定状态</CardDescription>
            </div>
            <Button onClick={handleEvolve} disabled={evolving || loading} className="shadow-md shadow-primary/10">
              {evolving ? "生成中..." : "生成未来大纲调整建议"}
            </Button>
          </CardHeader>
          <div className="px-6 pb-2 text-xs text-muted-foreground">
            提示：系统只会基于已定稿事实和已合并状态，为未写且未锁定的未来章节生成调整建议。已定稿章节不会被修改。
          </div>
          <CardContent className="flex-1 overflow-y-auto p-0 px-4 pb-4">
            <div className="space-y-4 pt-2">
              {loading ? (
                <div className="text-sm text-muted-foreground">加载中...</div>
              ) : outlineState?.chapters?.length > 0 ? (
                outlineState.chapters.map((ch: any) => (
                  <div key={ch.chapter_index} className="border rounded-md p-3 bg-card/50">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-semibold flex items-center gap-2">
                        <span>{ch.title || `第 ${ch.chapter_index} 章`}</span>
                        {ch.locked && <Lock className="h-3 w-3 text-red-400" />}
                      </div>
                      <Badge variant="outline" className={`
                        ${ch.status === 'finalized' ? 'border-emerald-500/50 text-emerald-400' : ''}
                        ${ch.status === 'drafted' ? 'border-amber-500/50 text-amber-400' : ''}
                        ${ch.status === 'planned' ? 'border-blue-500/50 text-blue-400' : ''}
                      `}>
                        {ch.status}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {ch.status === 'finalized' ? (ch.actual_summary || "暂无实际摘要") : (ch.planned_summary || "暂无计划摘要")}
                    </div>
                    {ch.notes && (
                      <div className="mt-2 text-xs bg-red-500/10 text-red-400 p-2 rounded">
                        {ch.notes}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted-foreground">暂无大纲数据，请生成新大纲或初始化旧项目。</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 右侧：状态补丁与演化建议 */}
      <div className="w-full md:w-80 lg:w-96 flex flex-col gap-4 overflow-y-auto pr-1">
        {/* 待处理状态补丁 */}
        <Card className="border-border/50 shadow-sm flex-1 flex flex-col overflow-hidden min-h-[280px]">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center justify-between">
              <span>待处理补丁 (State Patches)</span>
              {activePatches.length > 0 && (
                <Badge variant="destructive" className="animate-pulse">{activePatches.length}</Badge>
              )}
            </CardTitle>
            <CardDescription>定稿章节的状态变更记录，需要合并入设定集</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-0 px-4 pb-4">
            <div className="space-y-3 pt-2">
              {activePatches.length === 0 && !loading && (
                <div className="text-sm text-muted-foreground text-center py-8">暂无待处理补丁</div>
              )}
              {activePatches.map(patch => (
                <div
                  key={patch.patch_id}
                  className={`border rounded-lg p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                    patch.status === "pending_review" ? "border-amber-500/30 bg-amber-500/5" : "border-red-500/30 bg-red-500/5"
                  }`}
                  onClick={() => {
                    setSelectedPatch(patch)
                    setIsPatchModalOpen(true)
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold text-sm truncate pr-2">
                      第 {patch.chapter_index} 章 状态补丁
                    </div>
                    <Badge variant="outline" className={
                      patch.status === "pending_review" ? "text-amber-500 border-amber-500/50" : "text-red-500 border-red-500/50"
                    }>
                      {patch.status === "pending_review" ? "待审核" : "失败"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground line-clamp-2 mb-2">
                    {patch.summary_update || "暂无剧情摘要更新"}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] text-muted-foreground">{new Date(patch.created_at).toLocaleString()}</div>
                    {patch.risk_level === "high" && (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-red-500 border-red-500/30">
                        HIGH RISK
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 演化建议 Diff */}
        <Card className="border-border/50 shadow-sm flex-1 flex flex-col overflow-hidden min-h-[280px]">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">演化建议 (Outline Diffs)</CardTitle>
            <CardDescription>AI生成的未来调整方案</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-0 px-4 pb-4">
            <div className="space-y-3 pt-2">
              {diffs.length === 0 && !loading && (
                <div className="text-sm text-muted-foreground text-center py-4">暂无调整建议</div>
              )}
              {diffs.map(diff => (
                <div 
                  key={diff.diff_id} 
                  className={`border rounded-lg p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                    diff.status === "pending_review" ? "border-amber-500/30 bg-amber-500/5" : ""
                  }`}
                  onClick={() => {
                    setSelectedDiff(diff)
                    setIsDiffModalOpen(true)
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold text-sm truncate pr-2" title={diff.summary}>
                      {diff.summary || "大纲调整建议"}
                    </div>
                    <Badge variant="outline" className={
                      diff.status === "pending_review" ? "text-amber-500 border-amber-500/50" :
                      diff.status === "applied" ? "text-emerald-500 border-emerald-500/50" :
                      diff.status === "failed" ? "text-red-500 border-red-500/50" : "text-muted-foreground"
                    }>
                      {diff.status === "applied" ? "已应用" : diff.status === "discarded" ? "已放弃" : diff.status === "failed" ? "失败" : "待审查"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mb-2">
                    影响章节: {diff.affected_chapters?.join(", ")}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] text-muted-foreground">{new Date(diff.created_at).toLocaleString()}</div>
                    <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${
                      diff.risk_level === "high" ? "text-red-500 border-red-500/30" : 
                      diff.risk_level === "medium" ? "text-amber-500 border-amber-500/30" : 
                      "text-emerald-500 border-emerald-500/30"
                    }`}>
                      {diff.risk_level?.toUpperCase()} RISK
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 演化建议详情弹窗 */}
      <Dialog open={isDiffModalOpen} onOpenChange={setIsDiffModalOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>大纲调整建议详情</DialogTitle>
            <DialogDescription className="break-all">
              {selectedDiff?.summary}
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 overflow-y-auto pr-2 py-2 space-y-4">
            {selectedDiff?.risk_level === "high" && (
              <div className="flex items-start gap-2 bg-red-500/10 text-red-500 border border-red-500/20 rounded-md p-3 text-sm">
                <AlertTriangle className="h-5 w-5 shrink-0" />
                <div>
                  <div className="font-bold mb-1">高风险变更警告</div>
                  <div>该调整涉及秘密揭露、人物身份、核心关系、主线冲突或多章节规划变化。请确认后再应用。</div>
                </div>
              </div>
            )}
            
            {selectedDiff?.warnings?.length > 0 && (
              <div className="bg-red-500/5 border border-red-500/20 p-3 rounded-md space-y-1">
                <div className="font-semibold text-red-500 text-sm">验证错误/警告:</div>
                {selectedDiff.warnings.map((w: string, i: number) => (
                  <div key={i} className="text-sm text-red-400">• {w}</div>
                ))}
              </div>
            )}

            <div className="space-y-4">
              {selectedDiff?.changes?.map((change: any, i: number) => (
                <div key={i} className="border rounded-md overflow-hidden">
                  <div className="bg-muted/50 p-2 flex items-center justify-between border-b">
                    <span className="font-semibold text-sm">第 {change.chapter_index} 章: {change.change_type}</span>
                    <Badge variant="outline">{change.field || 'N/A'}</Badge>
                  </div>
                  <div className="p-3 text-sm">
                    <div className="mb-2">
                      <span className="font-semibold">原因:</span> {change.reason || '无'}
                    </div>
                    {change.change_type !== 'mark_conflict' && (
                      <div className="grid grid-cols-2 gap-4 mt-3">
                        <div className="border border-red-500/20 rounded p-2 bg-red-500/5">
                          <div className="text-xs text-red-400 font-semibold mb-1">修改前 (Before)</div>
                          <div className="whitespace-pre-wrap">{change.before}</div>
                        </div>
                        <div className="border border-emerald-500/20 rounded p-2 bg-emerald-500/5">
                          <div className="text-xs text-emerald-400 font-semibold mb-1">修改后 (After)</div>
                          <div className="whitespace-pre-wrap">{change.after}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <DialogFooter className="sm:justify-between pt-2 border-t mt-2">
            <div className="text-xs text-muted-foreground flex items-center gap-4">
              <span>状态: {selectedDiff?.status}</span>
              {selectedDiff?.pending_patch_ignored_count > 0 && (
                <span className="text-amber-500">已隔离 {selectedDiff.pending_patch_ignored_count} 个未合并补丁</span>
              )}
            </div>
            {selectedDiff?.status === "pending_review" ? (
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => handleDiscard(selectedDiff.diff_id)}>放弃此建议</Button>
                <Button variant="default" onClick={() => handleApply(selectedDiff.diff_id)}>确认应用此大纲调整</Button>
              </div>
            ) : (
              <Button variant="outline" onClick={() => setIsDiffModalOpen(false)}>关闭</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 状态补丁详情弹窗 */}
      <Dialog open={isPatchModalOpen} onOpenChange={setIsPatchModalOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>第 {selectedPatch?.chapter_index} 章 状态更新补丁详情</DialogTitle>
            <DialogDescription>
              请核对该定稿章节提取出的设定变更，合并后将写入人物设定与大纲数据库。
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto pr-2 py-2 space-y-4 text-sm">
            {selectedPatch?.risk_level === "high" && (
              <div className="flex items-start gap-2 bg-red-500/10 text-red-500 border border-red-500/20 rounded-md p-3">
                <AlertTriangle className="h-5 w-5 shrink-0" />
                <div>
                  <div className="font-bold mb-1">高风险设定变更</div>
                  <div>此补丁包含对人物身份、真实姓名、人物关系或核心设定的修改。请仔细确认。</div>
                </div>
              </div>
            )}

            {/* 剧情摘要 */}
            <div className="space-y-1">
              <div className="font-semibold text-muted-foreground flex items-center gap-1.5">
                <FileText className="h-4 w-4" /> 剧情摘要更新：
              </div>
              <div className="p-3 bg-muted/30 rounded border whitespace-pre-wrap">
                {selectedPatch?.summary_update || "无"}
              </div>
            </div>

            {/* 新增人物 */}
            {selectedPatch?.new_characters?.length > 0 && (
              <div className="space-y-1">
                <div className="font-semibold text-muted-foreground flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4" /> 新增人物：
                </div>
                <div className="space-y-2">
                  {selectedPatch.new_characters.map((ch: any, idx: number) => (
                    <div key={idx} className="p-3 border rounded-md bg-emerald-500/5 border-emerald-500/10">
                      <div className="font-semibold text-emerald-400">{ch.display_name} ({ch.id})</div>
                      <div className="text-xs mt-1"><span className="text-muted-foreground">定位：</span>{ch.role_in_story}</div>
                      <div className="text-xs mt-0.5"><span className="text-muted-foreground">当前状态：</span>{ch.current_status}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 人物设定变更 */}
            {selectedPatch?.character_updates?.length > 0 && (
              <div className="space-y-1">
                <div className="font-semibold text-muted-foreground flex items-center gap-1.5">
                  <Clock className="h-4 w-4" /> 人物状态更新：
                </div>
                <div className="space-y-2">
                  {selectedPatch.character_updates.map((ch: any, idx: number) => (
                    <div key={idx} className="p-3 border rounded-md bg-blue-500/5 border-blue-500/10">
                      <div className="font-semibold text-blue-400">角色 ID: {ch.id}</div>
                      {ch.true_name && <div className="text-xs mt-1"><span className="text-muted-foreground">真实姓名：</span>{ch.true_name}</div>}
                      {ch.current_status && <div className="text-xs mt-0.5"><span className="text-muted-foreground">当前状态更新：</span>{ch.current_status}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 人物关系变更 */}
            {selectedPatch?.relationship_updates?.length > 0 && (
              <div className="space-y-1">
                <div className="font-semibold text-muted-foreground flex items-center gap-1.5">
                  <ArrowRight className="h-4 w-4" /> 人物关系变化：
                </div>
                <div className="space-y-2">
                  {selectedPatch.relationship_updates.map((rel: any, idx: number) => (
                    <div key={idx} className="p-3 border rounded-md bg-purple-500/5 border-purple-500/10">
                      <div className="font-semibold text-purple-400">{rel.from} &rarr; {rel.to}</div>
                      <div className="text-xs mt-1"><span className="text-muted-foreground">新关系描述：</span>{rel.new_relationship}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 揭露的秘密与新秘密 */}
            {(selectedPatch?.revealed_secrets?.length > 0 || selectedPatch?.new_secrets?.length > 0) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedPatch?.revealed_secrets?.length > 0 && (
                  <div className="space-y-1 border rounded-md p-3 bg-amber-500/5 border-amber-500/10">
                    <div className="font-semibold text-amber-500 text-xs">已揭露的伏笔/秘密：</div>
                    <ul className="list-disc pl-4 text-xs space-y-1 text-muted-foreground mt-2">
                      {selectedPatch.revealed_secrets.map((sec: string, idx: number) => (
                        <li key={idx}>{sec}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {selectedPatch?.new_secrets?.length > 0 && (
                  <div className="space-y-1 border rounded-md p-3 bg-red-500/5 border-red-500/10">
                    <div className="font-semibold text-red-500 text-xs">新埋下的伏笔/秘密：</div>
                    <ul className="list-disc pl-4 text-xs space-y-1 text-muted-foreground mt-2">
                      {selectedPatch.new_secrets.map((sec: string, idx: number) => (
                        <li key={idx}>{sec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter className="sm:justify-between pt-2 border-t mt-2">
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              <span>补丁ID: {selectedPatch?.patch_id}</span>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => handleDiscardPatch(selectedPatch.patch_id)}>废弃此补丁</Button>
              <Button variant="default" onClick={() => handleMergePatch(selectedPatch.patch_id)}>合并到设定集</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
