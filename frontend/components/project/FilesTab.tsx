"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { RefreshCw, Copy, FileDown, Trash2, FileText, Loader2 } from "lucide-react"
import { useProjectContext } from "./ProjectContext"
import { useState, useCallback, useEffect, useRef } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"

const GENERATED_FILES = [
  {
    filename: "Novel_architecture.txt",
    label: "小说架构",
    description: "核心种子、角色架构、世界观和三幕式情节架构",
  },
  {
    filename: "architecture_core_seed.txt",
    label: "核心种子",
    description: "小说卖点、主角欲望、主线冲突和读者情绪承诺",
  },
  {
    filename: "architecture_character_dynamics.txt",
    label: "角色架构",
    description: "角色总览、人物详卡、关系冲突网、出场路线和写作约束",
  },
  {
    filename: "architecture_world_building.txt",
    label: "世界观",
    description: "故事规则、势力结构、资源体系和行动边界",
  },
  {
    filename: "architecture_plot.txt",
    label: "三幕式情节架构",
    description: "开局钩子、中段升级、后段爆发收束的全书主线",
  },
  {
    filename: "Novel_directory.txt",
    label: "章节目录",
    description: "章节标题和结构安排",
  },
  {
    filename: "global_summary.txt",
    label: "全局摘要",
    description: "架构初始化版全局摘要，定稿后持续更新",
  },
  {
    filename: "character_state.txt",
    label: "角色状态",
    description: "角色状态和关系变化",
  },
  {
    filename: "plot_arcs.txt",
    label: "伏笔暗线",
    description: "架构阶段生成的伏笔台账，章节定稿后持续更新",
  },
] as const

export function FilesTab() {
  const { projectId, activeTab, selectedOutputFile, setSelectedOutputFile } = useProjectContext()
  
  const [outputFileLoading, setOutputFileLoading] = useState(false)
  const [outputFileError, setOutputFileError] = useState("")
  const [outputFileContent, setOutputFileContent] = useState("")
  const [deleteOutputDialogOpen, setDeleteOutputDialogOpen] = useState(false)
  const outputFileRequestId = useRef(0)

  const loadOutputFile = useCallback(async (filename: string) => {
    if (!projectId) return
    const requestId = ++outputFileRequestId.current
    setOutputFileLoading(true)
    setOutputFileError("")
    try {
      const content = await api.files.get(projectId, filename)
      if (requestId !== outputFileRequestId.current) return
      setOutputFileContent(content)
    } catch (error: any) {
      if (requestId !== outputFileRequestId.current) return
      setOutputFileContent("")
      setOutputFileError(error?.message || `读取 ${filename} 失败`)
    } finally {
      if (requestId === outputFileRequestId.current) {
        setOutputFileLoading(false)
      }
    }
  }, [projectId])

  useEffect(() => {
    if (activeTab === "files" && selectedOutputFile) {
      loadOutputFile(selectedOutputFile)
    }
  }, [activeTab, selectedOutputFile, loadOutputFile])

  const handleCopyOutput = () => {
    navigator.clipboard.writeText(outputFileContent)
    toast.success("内容已复制到剪贴板")
  }

  const handleDownloadOutput = () => {
    const blob = new Blob([outputFileContent], { type: "text/plain;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = selectedOutputFile
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleDeleteOutputFile = async () => {
    try {
      await api.files.delete(projectId, selectedOutputFile)
      toast.success(`已删除 ${selectedOutputFile}`)
      setDeleteOutputDialogOpen(false)
      loadOutputFile(selectedOutputFile)
    } catch (error: any) {
      toast.error(error?.message || "删除失败")
    }
  }

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40">
        <CardHeader className="border-b border-border/30 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <CardTitle className="text-lg font-bold">生成文件管理</CardTitle>
              <CardDescription>集中查看架构、大纲、摘要、人物状态等创作底稿</CardDescription>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => loadOutputFile(selectedOutputFile)}
                disabled={outputFileLoading}
                className="bg-card/40 border-border/80 text-xs"
              >
                {outputFileLoading ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
                刷新
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyOutput}
                disabled={!outputFileContent || outputFileLoading}
                className="bg-card/40 border-border/80 text-xs"
              >
                <Copy className="h-3.5 w-3.5 mr-1.5" />
                复制
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadOutput}
                disabled={!outputFileContent || outputFileLoading}
                className="bg-card/40 border-border/80 text-xs"
              >
                <FileDown className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
                下载
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setDeleteOutputDialogOpen(true)}
                disabled={outputFileLoading}
                className="text-xs"
              >
                <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                删除
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
            {/* Sidebar list */}
            <div className="space-y-1.5">
              {GENERATED_FILES.map((file) => {
                const active = selectedOutputFile === file.filename
                return (
                  <button
                    key={file.filename}
                    type="button"
                    onClick={() => setSelectedOutputFile(file.filename)}
                    className={`w-full rounded-xl border p-3 text-left transition-all duration-200 ${
                      active
                        ? "border-primary/30 bg-primary/10 text-primary font-semibold shadow-inner"
                        : "hover:bg-accent/40 border-transparent hover:translate-x-0.5"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <FileText className={`h-4 w-4 shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`} />
                      <span className="font-semibold text-sm leading-tight">{file.label}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">{file.description}</p>
                  </button>
                )
              })}
            </div>

            {/* Document display screen */}
            <div className="rounded-xl border border-border/50 bg-secondary/10 flex flex-col overflow-hidden">
              <div className="flex items-center justify-between gap-3 border-b border-border/30 px-4 py-3 bg-secondary/35">
                <div className="min-w-0">
                  <p className="font-semibold text-sm">
                    {GENERATED_FILES.find((file) => file.filename === selectedOutputFile)?.label || selectedOutputFile}
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono mt-0.5">{selectedOutputFile}</p>
                </div>
                <Badge
                  variant="outline"
                  className={
                    outputFileLoading
                      ? "bg-secondary text-muted-foreground"
                      : outputFileError
                      ? "bg-destructive/10 text-destructive border-destructive/20"
                      : outputFileContent
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-secondary text-muted-foreground"
                  }
                >
                  {outputFileLoading ? "加载中" : outputFileError ? "读取错误" : outputFileContent ? "已同步" : "无内容"}
                </Badge>
              </div>
              <ScrollArea className="h-[60vh] bg-background/25">
                <div className="p-4">
                  {outputFileLoading ? (
                    <div className="space-y-4 py-4">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-4 w-5/6" />
                      <Skeleton className="h-4 w-2/3" />
                      <Skeleton className="h-4 w-4/5" />
                    </div>
                  ) : outputFileError ? (
                    <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-xs text-destructive leading-relaxed">
                      {outputFileError}
                    </div>
                  ) : outputFileContent ? (
                    <pre className="whitespace-pre-wrap break-words font-mono text-xs md:text-sm leading-6 tracking-wide text-foreground/90 pl-1 selection:bg-primary/20">
                      {outputFileContent}
                    </pre>
                  ) : (
                    <div className="text-center py-16 text-muted-foreground text-sm">
                      <FileText className="h-10 w-10 mx-auto mb-3 opacity-30 text-primary" />
                      <p>文件内容为空，请先在工作台生成相关产物</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>
          </div>
          <p className="mt-4 text-[11px] text-muted-foreground leading-normal">
            * 架构生成后会写入 <code>Novel_architecture.txt</code>、<code>global_summary.txt</code> 和 <code>plot_arcs.txt</code>，章节目录、角色状态也会分别保存在对应文件中。
          </p>
        </CardContent>
      </Card>

      <Dialog open={deleteOutputDialogOpen} onOpenChange={setDeleteOutputDialogOpen}>
        <DialogContent className="glass-panel border-border/45 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">确认删除生成文件</DialogTitle>
            <DialogDescription className="text-sm mt-1">
              将删除 <span className="font-semibold text-foreground">{GENERATED_FILES.find((file) => file.filename === selectedOutputFile)?.label || selectedOutputFile}</span>。
              {selectedOutputFile === "Novel_directory.txt" ? " 章节目录删除后，章节规划列表也会同步清空，但已生成的章节正文文件会保留。" : " 此操作不会影响其他生成文件。"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 gap-2">
            <Button variant="outline" onClick={() => setDeleteOutputDialogOpen(false)} className="hover:bg-accent/40">取消</Button>
            <Button variant="destructive" onClick={handleDeleteOutputFile}>确认删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
