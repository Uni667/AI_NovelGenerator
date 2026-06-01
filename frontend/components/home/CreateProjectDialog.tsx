"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useCreateProject } from "@/lib/hooks/use-projects"
import { toast } from "sonner"
import { PLATFORM_CONFIG } from "@/lib/types"

interface CreateProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateProjectDialog({ open, onOpenChange }: CreateProjectDialogProps) {
  const createProject = useCreateProject()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [platform, setPlatform] = useState("tomato")
  const [genre, setGenre] = useState("")
  const [numChapters, setNumChapters] = useState(10)
  const [wordNumber, setWordNumber] = useState(3000)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("项目名称不能为空")
      return
    }

    try {
      await createProject.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        platform,
        genre: genre.trim() || "都市",
        num_chapters: Number(numChapters),
        word_number: Number(wordNumber),
      })
      toast.success("项目创建成功！")
      onOpenChange(false)
      // Reset form
      setName("")
      setDescription("")
      setPlatform("tomato")
      setGenre("")
      setNumChapters(10)
      setWordNumber(3000)
    } catch (err: any) {
      toast.error(err?.message || "创建项目失败，请重试")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-background/95 backdrop-blur-xl border-border/60 p-6 rounded-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-foreground">新建小说创作项目</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              创建一个新的创作空间，开启大纲设计与AI协同创作。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-muted-foreground">项目名称 <span className="text-rose-500">*</span></label>
              <Input
                placeholder="请输入小说名称，例如：仙逆苍穹"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                required
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-muted-foreground">项目简介</label>
              <Textarea
                placeholder="简要描述小说核心亮点、受众、主角设定或题材概要..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="bg-black/20 border-border/60 focus:border-primary/50 text-xs min-h-[60px] rounded-lg"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">发布平台</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full bg-[#0A0915] border border-border/60 rounded-lg px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary/50 h-9"
                >
                  {Object.entries(PLATFORM_CONFIG).map(([key, config]) => (
                    <option key={key} value={key}>
                      {config.icon} {config.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">小说类型</label>
                <Input
                  placeholder="例如：都市、玄幻、古言"
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">规划总章节数</label>
                <Input
                  type="number"
                  min={1}
                  value={numChapters}
                  onChange={(e) => setNumChapters(parseInt(e.target.value) || 1)}
                  className="bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">单章规划字数</label>
                <Input
                  type="number"
                  min={500}
                  max={50000}
                  step={100}
                  value={wordNumber}
                  onChange={(e) => setWordNumber(parseInt(e.target.value) || 3000)}
                  className="bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                />
              </div>
            </div>
          </div>

          <DialogFooter className="pt-2 flex gap-2 justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs rounded-lg px-4"
              onClick={() => onOpenChange(false)}
            >
              取消
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-9 text-xs rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none font-semibold px-4"
              disabled={createProject.isPending}
            >
              {createProject.isPending ? "创建中..." : "确认创建"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
