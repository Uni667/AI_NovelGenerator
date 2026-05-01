"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useCreateProject } from "@/lib/hooks/use-projects"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { ArrowRight, Upload } from "lucide-react"

export default function NewProjectPage() {
  const router = useRouter()
  const createProject = useCreateProject()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    name: "",
    description: "",
    topic: "",
    genre: "玄幻",
    num_chapters: 10,
    word_number: 3000,
    user_guidance: "",
  })

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
            <CardDescription>设定小说的基本参数</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>项目名称 *</Label>
              <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="例如：星辰之海" />
            </div>
            <div>
              <Label>项目简介</Label>
              <Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="一句话描述你的小说" />
            </div>
            <div className="grid grid-cols-2 gap-4">
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
              <div>
                <Label>主题</Label>
                <Input value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} placeholder="故事的核心主题" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>章节数</Label>
                <Input type="number" value={form.num_chapters} onChange={e => setForm({ ...form, num_chapters: +e.target.value })} />
              </div>
              <div>
                <Label>每章目标字数</Label>
                <Input type="number" value={form.word_number} onChange={e => setForm({ ...form, word_number: +e.target.value })} />
              </div>
            </div>
            <Button onClick={() => setStep(2)} disabled={!form.name} className="w-full">
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
