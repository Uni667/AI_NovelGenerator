"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useCreateProject } from "@/lib/hooks/use-projects"
import { useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { PLATFORM_CONFIG } from "@/lib/types"
import { FolderOpen, Plus, Loader2 } from "lucide-react"

interface CreateProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateProjectDialog({ open, onOpenChange }: CreateProjectDialogProps) {
  const createProject = useCreateProject()
  const queryClient = useQueryClient()
  
  const [activeTab, setActiveTab] = useState<"new" | "import">("new")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [platform, setPlatform] = useState("tomato")
  const [genre, setGenre] = useState("")
  const [numChapters, setNumChapters] = useState(10)
  const [wordNumber, setWordNumber] = useState(3000)
  
  // Folder Import States
  const [folderPath, setFolderPath] = useState("")
  const [isImporting, setIsImporting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (activeTab === "new") {
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
    } else {
      if (!folderPath.trim()) {
        toast.error("本地文件夹路径不能为空")
        return
      }

      setIsImporting(true)
      try {
        const res = await api.projects.importLocalFolder(
          folderPath.trim(),
          name.trim() || undefined,
          platform,
          genre.trim() || undefined
        )
        toast.success(`项目导入成功：已从本地载入项目 "${res.name}"！`)
        queryClient.invalidateQueries({ queryKey: ["projects"] })
        onOpenChange(false)
        // Reset form
        setFolderPath("")
        setName("")
        setGenre("")
        setPlatform("tomato")
      } catch (err: any) {
        toast.error(err?.message || "导入本地文件夹失败，请检查路径是否正确且具有访问权限")
      } finally {
        setIsImporting(false)
      }
    }
  }

  const handleTabChange = (tab: "new" | "import") => {
    setActiveTab(tab)
    // Clear some inputs
    setName("")
    setGenre("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-background/95 backdrop-blur-xl border-border/60 p-6 rounded-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-foreground flex items-center gap-2">
              {activeTab === "new" ? <Plus className="w-5 h-5 text-primary" /> : <FolderOpen className="w-5 h-5 text-indigo-400" />}
              {activeTab === "new" ? "新建小说创作项目" : "从本地文件夹导入项目"}
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              {activeTab === "new"
                ? "创建一个全新的创作空间，开启大纲设计与AI协同创作。"
                : "输入电脑上的本地绝对路径，一键恢复备份或导入普通小说文本文件夹。"}
            </DialogDescription>
          </DialogHeader>

          {/* Tab Selector */}
          <div className="flex gap-1.5 p-1 bg-muted/60 border border-border/40 rounded-xl">
            <button
              type="button"
              onClick={() => handleTabChange("new")}
              className={`flex-1 text-center py-1.5 text-xs font-semibold rounded-lg transition-all ${
                activeTab === "new"
                  ? "bg-primary text-white shadow-md shadow-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/40"
              }`}
            >
              新建空白项目
            </button>
            <button
              type="button"
              onClick={() => handleTabChange("import")}
              className={`flex-1 text-center py-1.5 text-xs font-semibold rounded-lg transition-all ${
                activeTab === "import"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/40"
              }`}
            >
              本地文件夹导入
            </button>
          </div>

          <div className="space-y-3 py-1 text-xs">
            {/* Folder path - only for import mode */}
            {activeTab === "import" && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">
                  本地文件夹绝对路径 <span className="text-rose-500">*</span>
                </label>
                <Input
                  placeholder="例如 D:\NovelProjects\MyEpicBook 或 C:\Novels\MyStory"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  className="bg-background/50 dark:bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                  required
                />
                <p className="text-[10px] text-muted-foreground/60 leading-normal">
                  * 文件夹下包含 <code>metadata.json</code> 时导入备份；否则导入其中的所有 <code>.txt</code> 章节文件，章节名会自动关联为文件名对应的标题。
                </p>
              </div>
            )}

            {/* Project Name */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-muted-foreground">
                项目名称 {activeTab === "new" && <span className="text-rose-500">*</span>}
                {activeTab === "import" && <span className="text-muted-foreground/60"> (可选，默认使用文件夹名字)</span>}
              </label>
              <Input
                placeholder="请输入小说名称，例如：仙逆苍穹"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-background/50 dark:bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                required={activeTab === "new"}
              />
            </div>

            {/* Description - only for new project mode */}
            {activeTab === "new" && (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">项目简介</label>
                <Textarea
                  placeholder="简要描述小说核心亮点、受众、主角设定或题材概要..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="bg-background/50 dark:bg-black/20 border-border/60 focus:border-primary/50 text-xs min-h-[60px] rounded-lg"
                />
              </div>
            )}

            {/* Platform & Genre */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">发布平台</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full bg-background dark:bg-[#0A0915] border border-border/60 rounded-lg px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary/50 h-9"
                >
                  {Object.entries(PLATFORM_CONFIG).map(([key, config]) => (
                    <option key={key} value={key} className="bg-background dark:bg-[#0A0915]">
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
                  className="bg-background/50 dark:bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                />
              </div>
            </div>

            {/* Chapters & Word limits - only for new project mode */}
            {activeTab === "new" && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground">规划总章节数</label>
                  <Input
                    type="number"
                    min={1}
                    value={numChapters}
                    onChange={(e) => setNumChapters(parseInt(e.target.value) || 1)}
                    className="bg-background/50 dark:bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
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
                    className="bg-background/50 dark:bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 rounded-lg"
                  />
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="pt-2 flex gap-2 justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs rounded-lg px-4"
              onClick={() => onOpenChange(false)}
              disabled={createProject.isPending || isImporting}
            >
              取消
            </Button>
            <Button
              type="submit"
              size="sm"
              className={`h-9 text-xs rounded-lg text-white border-none font-semibold px-4 transition-all ${
                activeTab === "new" 
                  ? "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700" 
                  : "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700"
              }`}
              disabled={createProject.isPending || isImporting}
            >
              {createProject.isPending || isImporting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  {activeTab === "new" ? "创建中..." : "导入中..."}
                </>
              ) : (
                activeTab === "new" ? "确认创建" : "开始导入"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
