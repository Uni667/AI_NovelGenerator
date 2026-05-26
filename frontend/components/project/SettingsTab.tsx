"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Loader2, Save, Wand2, Settings2, Cpu, BrainCircuit, ShieldAlert } from "lucide-react"
import { PLATFORM_CONFIG, PLATFORMS, READER_DIRECTIONS, TREND_KEYS } from "@/lib/types"
import { useProjectContext } from "./ProjectContext"
import { useState, useEffect, useRef } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import debounce from "lodash/debounce"
import { cn } from "@/lib/utils"

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

  const getActiveProfile = (field: string) => {
    const assignedId = modelAssignment[field]
    if (assignedId) {
      return modelProfiles.find((p) => p.id === assignedId)
    }
    // 获取默认的主模型节点
    return modelProfiles.find((p) => p.is_default && p.type === "chat") || modelProfiles.find((p) => p.type === "chat")
  }

  const renderProfileBadge = (field: string) => {
    const assignedId = modelAssignment[field]
    const profile = getActiveProfile(field)
    if (!profile) return null

    const provider = (profile.provider || "").toLowerCase()
    let colorClasses = "bg-primary/5 text-primary border-primary/10"

    if (provider.includes("deepseek")) {
      colorClasses = "bg-purple-500/10 text-purple-400 border-purple-500/20"
    } else if (provider.includes("openai")) {
      colorClasses = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
    } else if (provider.includes("anthropic") || provider.includes("claude")) {
      colorClasses = "bg-orange-500/10 text-orange-400 border-orange-500/20"
    } else if (provider.includes("siliconflow") || provider.includes("silicon")) {
      colorClasses = "bg-blue-500/10 text-blue-400 border-blue-500/20"
    } else if (provider.includes("ollama")) {
      colorClasses = "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
    }

    return (
      <span className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border mt-1.5 transition-all w-fit",
        colorClasses
      )}>
        {assignedId ? "已专属分配" : "系统默认路由"}
      </span>
    )
  }

  // 动态合并平台分区
  const platformKey = config?.platform || "tomato"
  const categories = PLATFORM_CONFIG[platformKey]?.categories || []
  const displayCategories = config?.category && !categories.includes(config.category)
    ? [config.category, ...categories]
    : categories

  // 动态合并风格流派
  const genres = ["系统流", "重生流", "穿越流", "凡人流", "无敌流", "废柴流", "种田流", "无限流", "洪荒流", "末世流", "异能流", "灵气复苏", "诸天流", "反派流", "退婚流", "传统升级流", "其他"]
  const displayGenres = config?.genre && !genres.includes(config.genre)
    ? [config.genre, ...genres]
    : genres

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all duration-500">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl font-bold tracking-tight text-gradient-primary flex items-center gap-2">
            <Settings2 className="w-5 h-5 text-violet-400" /> 核心写作引擎参数
          </CardTitle>
          <CardDescription>配置小说发布的目标平台与核心流派基础参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
            {/* 1. 目标平台 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">发布目标平台</Label>
              <Select value={config?.platform || "tomato"} onValueChange={(v: string | null) => updateConfig.mutate({ platform: v || "tomato" })}>
                <SelectTrigger className="mt-1 shadow-sm transition-all focus:ring-primary/50 bg-background/30 rounded-xl border-border/60">
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

            {/* 3. 分类 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">大类分区</Label>
              <Select value={config?.category || ""} onValueChange={(v: string | null) => updateConfig.mutate({ category: v || "" })}>
                <SelectTrigger className="mt-1 shadow-sm transition-all focus:ring-primary/50 bg-background/30 rounded-xl border-border/60">
                  <SelectValue placeholder="选择分区" />
                </SelectTrigger>
                <SelectContent>
                  {displayCategories.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 4. 风格流派 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">风格流派</Label>
              <Select value={config?.genre || ""} onValueChange={(v: string | null) => updateConfig.mutate({ genre: v || "" })}>
                <SelectTrigger className="mt-1 shadow-sm transition-all focus:ring-primary/50 bg-background/30 rounded-xl border-border/60">
                  <SelectValue placeholder="选择流派" />
                </SelectTrigger>
                <SelectContent>
                  {displayGenres.map((g) => (
                    <SelectItem key={g} value={g}>{g}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 5. 核心主题 */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-muted-foreground">核心主题 (关键词/金手指)</Label>
              <Input
                defaultValue={config?.topic}
                placeholder="如：系统傍身、打脸逆袭、多马甲"
                className="mt-1 shadow-sm transition-all focus:ring-primary/50 bg-background/30 rounded-xl border-border/60"
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
                className="mt-1 shadow-sm transition-all focus:ring-primary/50 bg-background/30 rounded-xl border-border/60"
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
                className="mt-1 shadow-sm transition-all focus:ring-primary/50 bg-background/30 rounded-xl border-border/60"
                onBlur={(e) => debouncedUpdate({ word_number: Number(e.target.value) || 3000 })}
              />
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground mt-3 font-medium">
            💡 平台偏好：{PLATFORM_CONFIG[platformKey]?.description}
          </p>
        </CardContent>
      </Card>

      <Accordion defaultValue={[]} className="w-full space-y-4">
        {/* 高级创作细节与读者属性 - Collapsed by default */}
        <AccordionItem value="advanced-constraints" className="border-none">
          <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all duration-500 overflow-hidden">
            <AccordionTrigger className="px-6 py-4 hover:no-underline">
              <div className="flex flex-col items-start text-left">
                <CardTitle className="text-lg font-bold tracking-tight flex items-center gap-2">
                  <ShieldAlert className="w-4.5 h-4.5 text-amber-400" /> 高级创作约束与规避设定
                </CardTitle>
                <CardDescription className="mt-1 text-xs">设定文风基调、读者受众、社会情绪及避雷禁忌规则</CardDescription>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-6 pb-6 pt-0 space-y-4 border-t border-border/10 pt-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
                {/* Reader Direction */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">读者频道方向</Label>
                  <Select
                    value={config?.reader_direction || ""}
                    onValueChange={(v: string | null) => updateConfig.mutate({ reader_direction: v === "__none" ? "" : (v || "") })}
                  >
                    <SelectTrigger className="mt-1 bg-background/30 rounded-xl border-border/60">
                      <SelectValue placeholder="不限制" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none">不限制</SelectItem>
                      {READER_DIRECTIONS.map((d) => (
                        <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Target Reader */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">具体目标受众定位</Label>
                  <Input
                    defaultValue={config?.target_reader || ""}
                    placeholder="如：18-25岁年轻读者"
                    className="mt-1 bg-background/30 rounded-xl border-border/60"
                    onBlur={(e) => debouncedUpdate({ target_reader: e.target.value })}
                  />
                </div>

                {/* Trend Key */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">热点社会情绪参考</Label>
                  <Select
                    value={config?.trend_key || ""}
                    onValueChange={(v: string | null) => updateConfig.mutate({ trend_key: v === "__none" ? "" : (v || "") })}
                  >
                    <SelectTrigger className="mt-1 bg-background/30 rounded-xl border-border/60">
                      <SelectValue placeholder="无指定" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none">无指定</SelectItem>
                      {TREND_KEYS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Style Requirement */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-muted-foreground">文风基调要求</Label>
                <Input
                  defaultValue={config?.style_requirement || ""}
                  placeholder="例如：冷峻克制、快节奏爽文、热血搞笑、轻小说吐槽风"
                  className="bg-background/30 rounded-xl border-border/60"
                  onBlur={(e) => debouncedUpdate({ style_requirement: e.target.value })}
                />
              </div>

              {/* Forbidden Rules */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-muted-foreground">禁止改动设定 / 避雷限制</Label>
                <Textarea
                  defaultValue={config?.forbidden || ""}
                  placeholder="设定避雷红线，例如：千万不能洗白反派、单女主、主角绝对不当圣母等..."
                  rows={4}
                  className="bg-background/30 rounded-xl border-border/60 text-sm"
                  onBlur={(e) => debouncedUpdate({ forbidden: e.target.value })}
                />
              </div>
            </AccordionContent>
          </Card>
        </AccordionItem>

        {/* 全局大纲指令约束 */}
        <AccordionItem value="advanced-rules" className="border-none">
          <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all duration-500 overflow-hidden">
            <AccordionTrigger className="px-6 py-4 hover:no-underline">
              <div className="flex flex-col items-start text-left">
                <CardTitle className="text-lg font-bold tracking-tight flex items-center gap-2">
                  <BrainCircuit className="w-4.5 h-4.5 text-indigo-400" /> 全局大纲与长效上下文
                </CardTitle>
                <CardDescription className="mt-1 text-xs">输入小说底层的世界观、核心大纲逻辑与背景设定，长效生效</CardDescription>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-6 pb-6 pt-0 border-t border-border/10 pt-4">
              <div className="relative group">
                <Textarea
                  defaultValue={config?.user_guidance}
                  rows={10}
                  onBlur={(e) => debouncedUpdate({ user_guidance: e.target.value })}
                  placeholder="在此输入故事梗概、主角设定、反派逻辑、毒点规避及世界观基础规则约束等设定。大模型会在后续创作的所有章节自动读取该全局设定作为长文本上下文依据。"
                  className="w-full bg-background/30 border-border/60 focus:border-indigo-500/50 resize-y font-mono text-sm leading-relaxed p-4 rounded-xl shadow-inner transition-all focus:bg-background/80"
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
          <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all duration-500 overflow-hidden">
            <AccordionTrigger className="px-6 py-4 hover:no-underline">
              <div className="flex flex-col items-start text-left">
                <CardTitle className="text-lg font-bold tracking-tight flex items-center gap-2">
                  <Cpu className="w-4.5 h-4.5 text-emerald-400" /> AI 算力节点分配设置
                </CardTitle>
                <CardDescription className="mt-1 text-xs">为大纲、草稿、润色、审校分配最契合的底层大语言模型</CardDescription>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-6 pb-6 pt-0 border-t border-border/10 pt-4">
              <div className="mb-6 bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-emerald-400 flex items-center gap-1">
                    智能平台换挡 <Wand2 className="w-3.5 h-3.5" />
                  </h4>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    一键分析当前发布平台（{PLATFORM_CONFIG[platformKey]?.label.split(" / ")[0]}）调性，自动换挡分配最佳算力模型组。
                  </p>
                </div>
                <Button
                  variant="outline"
                  type="button"
                  onClick={handleApplyPlatformPreset}
                  disabled={platformPresetApplying}
                  className="h-9 border-emerald-500/30 hover:bg-emerald-500/10 hover:border-emerald-500/50 text-xs font-semibold transition-all active:scale-95 shadow-md shadow-emerald-500/5"
                >
                  {platformPresetApplying ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Wand2 className="h-4 w-4 mr-2 text-emerald-400" />
                  )}
                  应用最佳实践
                </Button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {([
                  { field: "architecture_profile_id", label: "架构生成算力节点" },
                  { field: "outline_profile_id", label: "章节目录算力节点" },
                  { field: "draft_profile_id", label: "章节草稿算力节点" },
                  { field: "polish_profile_id", label: "定稿润色算力节点" },
                  { field: "review_profile_id", label: "内容审校算力节点" },
                ] as const).map(({ field, label }) => (
                  <div key={field} className="flex flex-col justify-between p-3.5 rounded-xl bg-background/30 border border-border/60 hover:border-emerald-500/30 transition-all">
                    <div>
                      <Label className="text-xs font-bold text-muted-foreground">{label}</Label>
                      <Select
                        value={modelAssignment[field] || ""}
                        onValueChange={(v) =>
                          setModelAssignment((prev) => ({ ...prev, [field]: v || null }))
                        }
                      >
                        <SelectTrigger className="mt-1.5 border-border/40 bg-background/50 focus:ring-emerald-500/20 text-xs h-9 rounded-lg">
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
                    {renderProfileBadge(field)}
                  </div>
                ))}

                {/* Embedding 向量分配 */}
                <div className="flex flex-col justify-between p-3.5 rounded-xl bg-background/30 border border-border/60 hover:border-blue-500/30 transition-all">
                  <div>
                    <Label className="text-xs font-bold text-muted-foreground">知识检索算力节点 (Embedding)</Label>
                    <Select
                      value={modelAssignment["embedding_profile_id"] || ""}
                      onValueChange={(v) =>
                        setModelAssignment((prev) => ({ ...prev, embedding_profile_id: v || null }))
                      }
                    >
                      <SelectTrigger className="mt-1.5 border-border/40 bg-background/50 focus:ring-blue-500/20 text-xs h-9 rounded-lg">
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
                  {renderProfileBadge("embedding_profile_id")}
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <Button
                  onClick={handleSaveModelAssignment}
                  disabled={modelAssignmentSaving}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg shadow-emerald-600/10 active:scale-95 transition-all"
                >
                  {modelAssignmentSaving ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  保存算力分配配置
                </Button>
              </div>
            </AccordionContent>
          </Card>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
