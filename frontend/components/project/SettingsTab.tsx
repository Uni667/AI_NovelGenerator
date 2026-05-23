"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Loader2, Save, Wand2, Settings2, Cpu, BrainCircuit } from "lucide-react"
import { PLATFORM_CONFIG, PLATFORMS } from "@/lib/types"
import { useProjectContext } from "./ProjectContext"
import { useState, useEffect, useRef } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import debounce from "lodash/debounce"

export function SettingsTab() {
  const { projectId, config, updateConfig } = useProjectContext()

  const [modelProfiles, setModelProfiles] = useState<any[]>([])
  const [modelAssignment, setModelAssignment] = useState<Record<string, string | null>>({})
  const [modelAssignmentSaving, setModelAssignmentSaving] = useState(false)
  const [platformPresetApplying, setPlatformPresetApplying] = useState(false)

  const debouncedUpdate = useRef(
    debounce((data: Record<string, any>) => {
      updateConfig.mutate(data)
    }, 500)
  ).current

  useEffect(() => {
    if (!projectId) return
    api.config.listProfiles().then(setModelProfiles).catch(() => {})
    api.modelAssignment.get(projectId).then(setModelAssignment).catch(() => {})
  }, [projectId])

  const handleSaveModelAssignment = async () => {
    setModelAssignmentSaving(true)
    try {
      await api.modelAssignment.save(projectId, modelAssignment)
      toast.success("模型分配已保存")
    } catch (e: any) {
      toast.error(e?.message || "保存失败")
    } finally {
      setModelAssignmentSaving(false)
    }
  }

  const handleApplyPlatformPreset = async () => {
    const platform = config?.platform || "tomato"
    setPlatformPresetApplying(true)
    try {
      const assignment = await api.modelAssignment.applyPlatformPreset(projectId, platform)
      setModelAssignment(assignment || {})
      toast.success("已按当前平台自动换挡模型分配")
    } catch (error: any) {
      toast.error(error?.message || "平台换挡失败")
    } finally {
      setPlatformPresetApplying(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl font-bold tracking-tight text-gradient-primary flex items-center gap-2">
            <Settings2 className="w-5 h-5" /> 核心引擎参数
          </CardTitle>
          <CardDescription>配置小说的目标受众与全局架构维度</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
            {/* 1. 目标平台 */}
            <div className="space-y-1.5 flex flex-col justify-between">
              <div>
                <Label className="text-xs font-semibold text-muted-foreground">发布目标平台</Label>
                <Select value={config?.platform || "tomato"} onValueChange={(v) => updateConfig.mutate({ platform: v })}>
                  <SelectTrigger className="mt-1 shadow-sm transition-all focus:ring-primary/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PLATFORMS.map((key) => (
                      <SelectItem key={key} value={key}>
                        {PLATFORM_CONFIG[key].icon} {PLATFORM_CONFIG[key].label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 3. 分类 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">大类分区</Label>
              <Input
                defaultValue={config?.category}
                placeholder="例如：男频都市、女频言情"
                className="mt-1 shadow-sm transition-all focus:ring-primary/50"
                onBlur={(e) => debouncedUpdate({ category: e.target.value })}
              />
            </div>

            {/* 4. 风格流派 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">风格流派</Label>
              <Input
                defaultValue={config?.genre}
                placeholder="例如：神豪、爽文、无限流"
                className="mt-1 shadow-sm transition-all focus:ring-primary/50"
                onBlur={(e) => debouncedUpdate({ genre: e.target.value })}
              />
            </div>

            {/* 5. 核心主题 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">核心主题 (关键词/金手指)</Label>
              <Input
                defaultValue={config?.topic}
                placeholder="如：系统傍身、打脸逆袭、多马甲"
                className="mt-1 shadow-sm transition-all focus:ring-primary/50"
                onBlur={(e) => debouncedUpdate({ topic: e.target.value })}
              />
            </div>

            {/* 6. 规划章节 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">规划章节总数</Label>
              <Input
                type="number"
                min={1}
                defaultValue={config?.num_chapters}
                className="mt-1 shadow-sm transition-all focus:ring-primary/50"
                onBlur={(e) => debouncedUpdate({ num_chapters: Number(e.target.value) || 10 })}
              />
            </div>

            {/* 7. 每章字数 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">单章字数设定</Label>
              <Input
                type="number"
                min={500}
                step={500}
                defaultValue={config?.word_number}
                className="mt-1 shadow-sm transition-all focus:ring-primary/50"
                onBlur={(e) => debouncedUpdate({ word_number: Number(e.target.value) || 3000 })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Accordion type="single" collapsible defaultValue="advanced-rules" className="w-full space-y-4">
        {/* 高级全局指令 */}
        <AccordionItem value="advanced-rules" className="border-none">
          <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500 overflow-hidden">
            <AccordionTrigger className="px-6 py-4 hover:no-underline">
              <div className="flex flex-col items-start text-left">
                <CardTitle className="text-xl font-bold tracking-tight flex items-center gap-2">
                  <BrainCircuit className="w-5 h-5 text-indigo-400" /> 全局大纲指令约束
                </CardTitle>
                <CardDescription className="mt-1">输入小说底层的世界观、毒点规避及剧情基调约束，全流程生效</CardDescription>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-6 pb-6 pt-0">
              <div className="relative group">
                <Textarea
                  defaultValue={config?.user_guidance}
                  rows={10}
                  onBlur={(e) => debouncedUpdate({ user_guidance: e.target.value })}
                  placeholder="在此输入故事梗概、主角设定、反派逻辑、毒点规避及世界观基础规则约束等设定。大模型会在后续创作的所有章节自动读取该全局设定作为长文本上下文依据。"
                  className="w-full bg-background/50 border-input/50 focus:border-indigo-500/50 focus:ring-indigo-500/20 resize-y font-mono text-sm leading-relaxed p-4 rounded-xl shadow-inner transition-all group-hover:bg-background/80"
                />
                <div className="absolute right-3 bottom-3 text-[10px] text-muted-foreground bg-background/80 px-2 py-1 rounded border border-border/50 backdrop-blur-sm pointer-events-none">
                  AI Context Injected
                </div>
              </div>
            </AccordionContent>
          </Card>
        </AccordionItem>

        {/* 模型算力分配 */}
        <AccordionItem value="model-allocation" className="border-none">
          <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500 overflow-hidden">
            <AccordionTrigger className="px-6 py-4 hover:no-underline">
              <div className="flex flex-col items-start text-left">
                <div className="flex items-center justify-between w-full">
                  <CardTitle className="text-xl font-bold tracking-tight flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-emerald-400" /> AI 算力节点分配
                  </CardTitle>
                </div>
                <CardDescription className="mt-1">为大纲、草稿、润色分配最合适的底层大模型</CardDescription>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-6 pb-6 pt-0">
              <div className="mb-6 bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-emerald-400">智能平台换挡</h4>
                  <p className="text-xs text-muted-foreground mt-1">根据当前发布平台，自动将最适合的模型分配给各个创作节点。</p>
                </div>
                <Button
                  variant="outline"
                  onClick={handleApplyPlatformPreset}
                  disabled={platformPresetApplying}
                  className="h-9 border-emerald-500/30 hover:bg-emerald-500/10 text-xs font-semibold shadow-glow transition-all"
                >
                  {platformPresetApplying ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Wand2 className="h-4 w-4 mr-2 text-emerald-400" />
                  )}
                  应用最佳实践
                </Button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
                {([
                  { field: "architecture_profile_id", label: "架构生成算力节点" },
                  { field: "outline_profile_id", label: "章节目录算力节点" },
                  { field: "draft_profile_id", label: "章节草稿算力节点" },
                  { field: "polish_profile_id", label: "定稿润色算力节点" },
                  { field: "review_profile_id", label: "内容审校算力节点" },
                ] as const).map(({ field, label }) => (
                  <div key={field} className="space-y-1.5 p-3 rounded-lg bg-background/30 border border-border/50 hover:border-emerald-500/30 transition-colors">
                    <Label className="text-xs font-bold text-muted-foreground">{label}</Label>
                    <Select
                      value={modelAssignment[field] || ""}
                      onValueChange={(v) =>
                        setModelAssignment((prev) => ({ ...prev, [field]: v || null }))
                      }
                    >
                      <SelectTrigger className="mt-1 border-transparent bg-background/50 focus:ring-emerald-500/20 text-xs h-8">
                        <SelectValue placeholder="采用系统全局默认" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">采用系统全局默认</SelectItem>
                        {modelProfiles
                          .filter((p) => p.type === "chat" && p.is_active)
                          .sort((a, b) => (a.name || "").localeCompare(b.name || ""))
                          .map((p) => (
                             <SelectItem key={p.id} value={p.id}>
                              {p.name} ({p.provider}/{p.model})
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}

                {/* Embedding 向量分配 */}
                <div className="space-y-1.5 p-3 rounded-lg bg-background/30 border border-border/50 hover:border-blue-500/30 transition-colors">
                  <Label className="text-xs font-bold text-muted-foreground">知识检索算力节点 (Embedding)</Label>
                  <Select
                    value={modelAssignment["embedding_profile_id"] || ""}
                    onValueChange={(v) =>
                      setModelAssignment((prev) => ({ ...prev, embedding_profile_id: v || null }))
                    }
                  >
                    <SelectTrigger className="mt-1 border-transparent bg-background/50 focus:ring-blue-500/20 text-xs h-8">
                      <SelectValue placeholder="不启用向量嵌入检索" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">不启用向量嵌入检索</SelectItem>
                      {modelProfiles
                        .filter((p) => p.type === "embedding" && p.is_active)
                        .sort((a, b) => (a.name || "").localeCompare(b.name || ""))
                        .map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.name} ({p.provider}/{p.model})
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <Button
                  onClick={handleSaveModelAssignment}
                  disabled={modelAssignmentSaving}
                  className="shadow-glow"
                >
                  {modelAssignmentSaving ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  保存节点配置
                </Button>
              </div>
            </AccordionContent>
          </Card>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
