"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useCreateProject } from "@/lib/hooks/use-projects"
import { PLATFORM_CONFIG, PLATFORMS } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { ArrowRight } from "lucide-react"

export default function NewProjectPage() {
  const router = useRouter()
  const createProject = useCreateProject()
  const [step, setStep] = useState(1)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({
    name: "",
    platform: "tomato" as string,
    category: "",
    description: "",
    topic: "",
    genre: "玄幻",
    num_chapters: 10,
    word_number: 3000,
    user_guidance: "",
  })

  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {}
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

  const handleCreate = async () => {
    const result = await createProject.mutateAsync(form)
    router.push(`/projects/${result.id}`)
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">新建小说项目</h1>
      <p className="text-muted-foreground mb-8">只需两步，AI 就能帮你开始创作</p>

      {/* 步骤指示器 */}
      <div className="flex items-center gap-4 mb-8">
        <div className={`flex items-center gap-2 ${step >= 1 ? "text-primary" : "text-muted-foreground"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted"}`}>1</div>
          <span className="font-medium">基本信息</span>
        </div>
        <Separator className="flex-1" />
        <div className={`flex items-center gap-2 ${step >= 2 ? "text-primary" : "text-muted-foreground"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted"}`}>2</div>
          <span className="font-medium">大纲与知识库</span>
        </div>
      </div>

      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>第一步：基本信息</CardTitle>
            <CardDescription>选择目标平台，设定小说的基本参数</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* 平台选择 */}
            <div>
              <Label>目标平台</Label>
              <p className="text-xs text-muted-foreground mb-2">选择小说将要发布的平台，分类和工具将据此适配</p>
              <div className="grid grid-cols-2 gap-3">
                {PLATFORMS.map((key) => {
                  const p = PLATFORM_CONFIG[key]
                  const selected = form.platform === key
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setForm({ ...form, platform: key, category: "" })}
                      className={cn(
                        "flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left",
                        selected
                          ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                          : "border-border hover:border-primary/50 hover:bg-accent"
                      )}
                    >
                      <span className="text-2xl">{p.icon}</span>
                      <div>
                        <span className="font-medium text-sm block">{p.label}</span>
                        <span className="text-xs text-muted-foreground">{p.categories.length} 个分类</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <Separator />

            {/* 书名（可选） */}
            <div>
              <Label>项目名称</Label>
              <p className="text-xs text-muted-foreground mb-1">可选，没想好可以先不填</p>
              <Input
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="暂未命名，可后续修改"
              />
            </div>

            <div>
              <Label>项目简介</Label>
              <Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="一句话描述你的小说" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>分类</Label>
                <Select value={form.category} onValueChange={(v) => v && setForm({ ...form, category: v })}>
                  <SelectTrigger><SelectValue placeholder="选择分类" /></SelectTrigger>
                  <SelectContent>
                    {PLATFORM_CONFIG[form.platform]?.categories.map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  根据 {PLATFORM_CONFIG[form.platform]?.label} 的分类体系
                </p>
              </div>
              <div>
                <Label>类型</Label>
                <Select value={form.genre} onValueChange={(v) => v && setForm({ ...form, genre: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["玄幻", "都市", "科幻", "仙侠", "悬疑", "历史", "言情", "武侠", "轻小说"].map(g => (
                      <SelectItem key={g} value={g}>{g}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>主题</Label>
                <Input value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} placeholder="故事的核心主题" />
              </div>
              <div>
                <Label>章节数</Label>
                <Input
                  type="number"
                  value={form.num_chapters}
                  onChange={e => setForm({ ...form, num_chapters: +e.target.value })}
                  min={1}
                  className={errors.num_chapters ? "border-destructive" : ""}
                />
                {errors.num_chapters && <p className="text-xs text-destructive mt-1">{errors.num_chapters}</p>}
              </div>
            </div>

            <div>
              <Label>每章目标字数</Label>
              <Input
                type="number"
                value={form.word_number}
                onChange={e => setForm({ ...form, word_number: +e.target.value })}
                min={500}
                max={50000}
                className={errors.word_number ? "border-destructive" : ""}
              />
              {errors.word_number && <p className="text-xs text-destructive mt-1">{errors.word_number}</p>}
            </div>

            <Button onClick={() => { if (validateStep1()) setStep(2) }} className="w-full">
              下一步 <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>第二步：大纲与知识库</CardTitle>
            <CardDescription>提供更详细的创作指导——这里的内容会直接影响 AI 生成的架构和章节</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>内容指导（大纲）</Label>
              <Textarea
                value={form.user_guidance}
                onChange={e => setForm({ ...form, user_guidance: e.target.value })}
                placeholder={"在这里写下你的大纲、世界观设定、角色构想、情节走向...\n\n例如：\n- 主角是一个在科技公司打工的普通程序员\n- 某天他发现自己写的代码能改变现实\n- 世界存在一个隐藏的修仙组织...\n\n越详细，AI 生成的内容越贴近你的想法。"}
                rows={12}
              />
              <p className="text-xs text-muted-foreground mt-1">
                提示：创建项目后，你还可以通过「导入知识库」功能上传更详细的设定文档（如 TXT 文件），AI 在写章节时会自动检索相关内容。
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep(1)}>上一步</Button>
              <Button onClick={handleCreate} disabled={createProject.isPending} className="flex-1">
                {createProject.isPending ? "创建中..." : "创建项目并开始写作"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
