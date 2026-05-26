"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useCreateProject } from "@/lib/hooks/use-projects"
import { PLATFORM_CONFIG, PLATFORMS, READER_DIRECTIONS, TREND_KEYS } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { ArrowRight, Sparkles, Loader2, ChevronDown, ChevronUp, Check, ArrowLeft } from "lucide-react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export default function NewProjectPage() {
  const router = useRouter()
  const createProject = useCreateProject()
  const [step, setStep] = useState(1)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isInferring, setIsInferring] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [form, setForm] = useState({
    name: "",
    platform: "tomato" as string,
    category: "",
    description: "",
    topic: "",
    genre: "",
    num_chapters: 10,
    word_number: 3000,
    user_guidance: "",
    target_reader: "",
    reader_direction: "",
    trend_key: "",
    forbidden: "",
    style_requirement: "",
  })

  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {}
    if (!form.name.trim()) {
      newErrors.name = "请输入小说项目名称"
    }
    if (form.num_chapters < 1) {
      newErrors.num_chapters = "章节数至少为 1"
    }
    if (form.word_number < 500) {
      newErrors.word_number = "每章字数至少 500"
    }
    if (form.word_number > 50000) {
      newErrors.word_number = "每章字数不能超过 50000"
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleAiInfer = async () => {
    if (!form.user_guidance.trim()) {
      toast.warning("请输入大纲或故事梗概，让 AI 帮您智能推断配置")
      return
    }
    setIsInferring(true)
    try {
      const res = await api.projects.inferConfig({
        user_guidance: form.user_guidance,
        platform: form.platform,
      })
      if (res.success && res.data) {
        const d = res.data
        setForm((prev) => ({
          ...prev,
          name: prev.name || d.name || "",
          category: d.category || prev.category || "",
          genre: d.genre || prev.genre || "",
          topic: d.topic || prev.topic || "",
          target_reader: d.target_reader || prev.target_reader || "",
          style_requirement: d.style_requirement || prev.style_requirement || "",
          forbidden: d.forbidden || prev.forbidden || "",
          description: prev.description || d.topic || "",
        }))
        toast.success("✨ AI 一键智能装载完成！已推断书名、流派及高级约束设定。")
      } else {
        toast.error("智能解析失败，请检查模型节点配置")
      }
    } catch (e: any) {
      toast.error(e?.message || "智能解析失败，请稍后重试")
    } finally {
      setIsInferring(false)
    }
  }

  const handleCreate = async () => {
    try {
      const result = await createProject.mutateAsync(form)
      toast.success("项目创建成功，进入创作空间！")
      router.push(`/projects/${result.id}`)
    } catch (e: any) {
      toast.error(e?.message || "项目创建失败，请检查表单参数")
    }
  }

  // 动态合并平台配置和 AI 推断的分类
  const categories = PLATFORM_CONFIG[form.platform]?.categories || []
  const displayCategories = form.category && !categories.includes(form.category)
    ? [form.category, ...categories]
    : categories

  // 动态合并流派配置
  const genres = ["系统流", "重生流", "穿越流", "凡人流", "无敌流", "废柴流", "种田流", "无限流", "洪荒流", "末世流", "异能流", "灵气复苏", "诸天流", "反派流", "退婚流", "传统升级流", "其他"]
  const displayGenres = form.genre && !genres.includes(form.genre)
    ? [form.genre, ...genres]
    : genres

  return (
    <div className="max-w-3xl mx-auto pb-12">
      <div className="mb-6">
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => router.push("/")}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          返回项目列表
        </Button>
      </div>
      <div className="text-center mb-8">
        <h1 className="text-4xl font-extrabold tracking-tight mb-3 text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-indigo-400 to-cyan-400">
          新建小说创作项目
        </h1>
        <p className="text-muted-foreground text-sm">
          通过智能分析将灵感直接转化为小说元数据，精简参数设定流程
        </p>
      </div>

      {/* 步骤指示器 */}
      <div className="flex items-center justify-center gap-4 mb-8 max-w-md mx-auto">
        <div className={cn("flex items-center gap-2 transition-all duration-300", step >= 1 ? "text-primary scale-105" : "text-muted-foreground")}>
          <div className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-lg transition-all duration-300", step >= 1 ? "bg-primary text-primary-foreground shadow-primary/20" : "bg-muted")}>1</div>
          <span className="font-semibold text-sm">灵感与核心属性</span>
        </div>
        <Separator className="flex-1 max-w-[80px]" />
        <div className={cn("flex items-center gap-2 transition-all duration-300", step >= 2 ? "text-primary scale-105" : "text-muted-foreground")}>
          <div className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-lg transition-all duration-300", step >= 2 ? "bg-primary text-primary-foreground shadow-primary/20" : "bg-muted")}>2</div>
          <span className="font-semibold text-sm">高级约束与预览</span>
        </div>
      </div>

      {step === 1 && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
          {/* Card 1: Platform & Outline */}
          <Card className="glass-panel border-border/40 bg-card/40 backdrop-blur-md hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all duration-500">
            <CardHeader>
              <CardTitle className="text-lg font-bold flex items-center gap-2 text-violet-400">
                <Sparkles className="w-4 h-4" /> 1. 创作平台与核心梗概
              </CardTitle>
              <CardDescription>选择您的小说发布平台并提供简单的故事创意，支持 AI 一键配置</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Platform Cards */}
              <div className="space-y-2">
                <Label className="text-xs font-semibold text-muted-foreground">发布目标平台</Label>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {PLATFORMS.map((key) => {
                    const p = PLATFORM_CONFIG[key]
                    const selected = form.platform === key
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setForm({ ...form, platform: key, category: "" })}
                        className={cn(
                          "flex flex-col items-center justify-center p-3 rounded-xl border transition-all text-center gap-1.5",
                          selected
                            ? "border-violet-500/50 bg-violet-500/5 ring-1 ring-violet-500/30 shadow-[0_0_15px_rgba(139,92,246,0.1)] text-foreground scale-[1.02]"
                            : "border-border/60 hover:border-violet-500/30 hover:bg-accent/40 text-muted-foreground"
                        )}
                      >
                        <span className="text-xl">{p.icon}</span>
                        <div className="leading-tight">
                          <span className="font-semibold text-xs block">{p.label.split(" / ")[0]}</span>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Outline / Guidance & AI inference */}
              <div className="space-y-2 relative">
                <div className="flex justify-between items-center">
                  <Label className="text-xs font-semibold text-muted-foreground">核心故事大纲 / 梗概创意</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={isInferring}
                    onClick={handleAiInfer}
                    className="h-8 text-xs font-bold bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none shadow-md shadow-indigo-600/10 hover:shadow-indigo-600/20 active:scale-95 transition-all flex items-center gap-1"
                  >
                    {isInferring ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        AI 智能分析中...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        AI 一键智能开书
                      </>
                    )}
                  </Button>
                </div>
                <Textarea
                  value={form.user_guidance}
                  onChange={e => setForm({ ...form, user_guidance: e.target.value })}
                  placeholder={"在这里输入您的核心创意大纲...\n例如：\n- 主角是个熬夜写代码被裁员的程序员\n- 得到神奇的“代码编辑器系统”，在虚拟修仙网游中编写Bug改变物理规律\n- 杀伐果断，从新手村一路破开维度成仙..."}
                  rows={6}
                  className="bg-background/40 focus:bg-background/80 transition-all font-sans text-sm leading-relaxed p-3.5 rounded-xl border-border/60"
                />
                <p className="text-[10px] text-muted-foreground">
                  💡 输入故事大纲后，点击右上角【AI一键智能开书】按钮可自动帮您填写书名、分类、风格及约束。
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Extracted / Standard parameters */}
          <Card className="glass-panel border-border/40 bg-card/40 backdrop-blur-md hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.05)] transition-all duration-500">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold flex items-center gap-2 text-indigo-400">
                2. 核心属性参数设定
              </CardTitle>
              <CardDescription>您可以修改 AI 智能推断的参数，或直接手动录入核心属性</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Book Name */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">小说名称</Label>
                  <Input
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="请输入书名（或使用 AI 一键推断）"
                    className={cn("bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60", errors.name && "border-destructive")}
                  />
                  {errors.name && <p className="text-[11px] text-destructive">{errors.name}</p>}
                </div>

                {/* Theme / Topic */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">核心主题 (金手指/主要卖点)</Label>
                  <Input
                    value={form.topic}
                    onChange={e => setForm({ ...form, topic: e.target.value })}
                    placeholder="例如：系统流、代码修仙、神豪反利"
                    className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60"
                  />
                </div>

                {/* Category */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">大类分区</Label>
                  <Select value={form.category} onValueChange={(v: string | null) => setForm({ ...form, category: v || "" })}>
                    <SelectTrigger className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60">
                      <SelectValue placeholder="选择大类分区" />
                    </SelectTrigger>
                    <SelectContent>
                      {displayCategories.map((c) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Genre */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">风格/流派</Label>
                  <Select value={form.genre} onValueChange={(v: string | null) => setForm({ ...form, genre: v || "" })}>
                    <SelectTrigger className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60">
                      <SelectValue placeholder="选择流派" />
                    </SelectTrigger>
                    <SelectContent>
                      {displayGenres.map((g) => (
                        <SelectItem key={g} value={g}>{g}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Chapters */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">规划章节总数</Label>
                  <Input
                    type="number"
                    value={form.num_chapters}
                    onChange={e => setForm({ ...form, num_chapters: parseInt(e.target.value) || 0 })}
                    min={1}
                    className={cn("bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60", errors.num_chapters && "border-destructive")}
                  />
                  {errors.num_chapters && <p className="text-[11px] text-destructive">{errors.num_chapters}</p>}
                </div>

                {/* Single Chapter Words */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">每章字数设定</Label>
                  <Input
                    type="number"
                    value={form.word_number}
                    onChange={e => setForm({ ...form, word_number: parseInt(e.target.value) || 0 })}
                    min={500}
                    max={50000}
                    className={cn("bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60", errors.word_number && "border-destructive")}
                  />
                  {errors.word_number && <p className="text-[11px] text-destructive">{errors.word_number}</p>}
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1.5 mt-2">
                <Label className="text-xs font-semibold text-muted-foreground">一句话项目简介</Label>
                <Input
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="用一句话描述你的小说项目"
                  className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60"
                />
              </div>
            </CardContent>
          </Card>

          <Button
            type="button"
            onClick={() => {
              if (validateStep1()) {
                setStep(2)
              } else {
                toast.error("请完善核心属性参数")
              }
            }}
            className="w-full h-11 font-bold text-sm bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white rounded-xl shadow-lg shadow-indigo-600/10 active:scale-98 transition-all flex items-center justify-center gap-1.5"
          >
            配置高级细节约束并预览
            <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
          {/* Summary Preview */}
          <Card className="glass-panel border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader className="pb-3 border-b border-border/20">
              <CardTitle className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-indigo-400">
                核心配置概览
              </CardTitle>
              <CardDescription>请核对您的核心开书信息</CardDescription>
            </CardHeader>
            <CardContent className="pt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-xs text-muted-foreground block">发布平台</span>
                <span className="font-semibold flex items-center gap-1 mt-0.5">
                  {PLATFORM_CONFIG[form.platform]?.icon} {PLATFORM_CONFIG[form.platform]?.label.split(" / ")[0]}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">小说书名</span>
                <span className="font-semibold text-foreground mt-0.5 block truncate">{form.name}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">分类 / 流派</span>
                <span className="font-semibold text-foreground mt-0.5 block truncate">
                  {form.category} / {form.genre}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">规划章节与字数</span>
                <span className="font-semibold text-foreground mt-0.5">
                  {form.num_chapters}章 × {form.word_number}字
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Advanced Constraints Panel - Collapsed by default */}
          <Card className="glass-panel border-border/40 bg-card/40 backdrop-blur-md overflow-hidden transition-all duration-300">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-accent/20 transition-all"
            >
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2 text-violet-400">
                  <Check className="w-4 h-4 text-emerald-400" /> 高级创作细节与规避约束
                </CardTitle>
                <CardDescription className="mt-0.5 text-xs">
                  文风基调、特定避雷点、目标读者定位与热点情绪偏好（默认折叠，建议由 AI 自动推断）
                </CardDescription>
              </div>
              {showAdvanced ? (
                <ChevronUp className="w-5 h-5 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-5 h-5 text-muted-foreground" />
              )}
            </button>

            {showAdvanced && (
              <CardContent className="px-6 pb-6 pt-2 space-y-4 border-t border-border/20 animate-in fade-in duration-300">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Reader Direction */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-muted-foreground">读者频道方向</Label>
                    <Select
                      value={form.reader_direction}
                      onValueChange={(v: string | null) => setForm({ ...form, reader_direction: v === "__none" ? "" : (v || "") })}
                    >
                      <SelectTrigger className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60">
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
                      value={form.target_reader}
                      onChange={e => setForm({ ...form, target_reader: e.target.value })}
                      placeholder="例如：25-35岁上班族爽文受众"
                      className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60"
                    />
                  </div>
                </div>

                {/* Trend Key */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">热点社会情绪参考</Label>
                  <Select
                    value={form.trend_key}
                    onValueChange={(v: string | null) => setForm({ ...form, trend_key: v === "__none" ? "" : (v || "") })}
                  >
                    <SelectTrigger className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60">
                      <SelectValue placeholder="无指定（AI 自动处理）" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none">无指定</SelectItem>
                      {TREND_KEYS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    系统会自动在剧情冲突中隐性转译此类心理情绪，绝非直接引用现实事件。
                  </p>
                </div>

                {/* Style Requirement */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">文风基调要求</Label>
                  <Input
                    value={form.style_requirement}
                    onChange={e => setForm({ ...form, style_requirement: e.target.value })}
                    placeholder="例如：轻松搞笑吐槽风、克制冷峻正剧向"
                    className="bg-background/40 focus:bg-background/80 transition-all rounded-xl border-border/60"
                  />
                </div>

                {/* Forbidden Rules */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-muted-foreground">禁止改动设定 / 避雷限制</Label>
                  <Textarea
                    value={form.forbidden}
                    onChange={e => setForm({ ...form, forbidden: e.target.value })}
                    placeholder="告诉 AI 哪些限制绝对不能改变：&#10;1. 主角必须单女主，绝无暧昧&#10;2. 不能洗白反派，恶人必须受到惩罚"
                    rows={4}
                    className="bg-background/40 focus:bg-background/80 transition-all font-sans text-sm leading-relaxed p-3 rounded-xl border-border/60"
                  />
                </div>
              </CardContent>
            )}
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep(1)}
              className="h-11 px-5 border-border hover:bg-accent/40 rounded-xl"
            >
              返回修改核心属性
            </Button>
            <Button
              type="button"
              onClick={handleCreate}
              disabled={createProject.isPending}
              className="flex-1 h-11 font-bold text-sm bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white rounded-xl shadow-lg shadow-indigo-600/15 active:scale-98 transition-all flex items-center justify-center gap-1.5"
            >
              {createProject.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  正在开书并构建创作空间...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  智能开书并开始写作
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
