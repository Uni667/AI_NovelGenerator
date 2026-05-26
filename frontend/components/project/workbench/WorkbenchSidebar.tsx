"use client"

import React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2, Upload, Sparkles } from "lucide-react"
import { useProjectContext } from "../ProjectContext"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import type { Chapter } from "@/lib/types"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"

export function WorkbenchSidebar() {
  const {
    projectId,
    chapters,
    batchUploading,
    setBatchUploading,
    batchFileRef,
    refetchChapters,
    generation,
    workbench: {
      selectedChapterNumber, setSelectedChapterNumber,
    },
    platform: {
      setHookChapterNum
    }
  } = useProjectContext()

  const {
    isConnected,
    generationTaskId,
    generationStopping,
    startTask,
    enableBrainstorming,
    setEnableBrainstorming,
    batchChapterCount,
    setBatchChapterCount,
  } = generation

  const completedChapters = chapters?.filter((c: Chapter) => c.status === "final").length || 0
  const draftChapters = chapters?.filter((c: Chapter) => c.status === "draft").length || 0
  const pendingChapters = chapters?.filter((c: Chapter) => c.status === "pending").length || 0

  const handleBatchUploadChapters = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setBatchUploading(true)
    try {
      await api.chapters.upload(projectId, Array.from(files))
      toast.success(`成功导入 ${files.length} 个章节`)
      refetchChapters()
    } catch (error) {
      toast.error((error as Error).message || "导入章节失败")
    } finally {
      setBatchUploading(false)
      if (batchFileRef.current) batchFileRef.current.value = ""
    }
  }

  const handleGenerateChapterBatch = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      const url = `/api/v1/projects/${projectId}/generate/chapters?start_chapter=${selectedChapterNumber}&count=${batchChapterCount}${enableBrainstorming ? "&enable_brainstorming=true" : ""}`
      startTask("chapterBatch", url, taskId)
      toast.success("已发起批量生成，请在右侧编辑区关注生成进度。")
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  return (
    <Card className="glass-panel border-border/40 h-full flex flex-col hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
      <CardHeader className="pb-4 shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold text-gradient-primary w-fit">章节目录</CardTitle>
          <div className="flex items-center gap-2">
            {/* AI Batch Generate Dialog */}
            <Dialog>
              <DialogTrigger className="flex items-center justify-center h-8 w-8 rounded-md text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 transition-colors animate-pulse" title="批量生成章节">
                <Sparkles className="h-4 w-4" />
              </DialogTrigger>
              <DialogContent className="max-w-sm bg-background/95 backdrop-blur-xl border-border/60 p-5 rounded-2xl">
                <DialogHeader>
                  <DialogTitle className="text-base font-bold flex items-center gap-2 text-violet-400">
                    <Sparkles className="h-4.5 w-4.5" />
                    批量生成章节草稿
                  </DialogTitle>
                  <DialogDescription className="text-xs text-muted-foreground/80 mt-1">
                    从当前选定的第 {selectedChapterNumber} 章开始，按照小说目录大纲依次自动生成草稿。
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 my-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground font-semibold">起始章节位置</Label>
                    <Input
                      type="text"
                      disabled
                      value={`第 ${selectedChapterNumber} 章 (从该章节起往后顺序生成)`}
                      className="bg-muted/40 text-muted-foreground border-border/60 h-9 rounded-lg"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground font-semibold">本轮生成章数 (上限 20 章)</Label>
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={batchChapterCount}
                      onChange={(e) => setBatchChapterCount(Math.min(20, Math.max(1, Number(e.target.value) || 1)))}
                      className="bg-background/40 focus:bg-background/85 border-border/60 h-9 rounded-lg"
                    />
                  </div>
                  <div className="flex items-center space-x-2 bg-primary/5 p-3 rounded-xl border border-primary/10 mt-1">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={enableBrainstorming}
                      disabled={isConnected || Boolean(generationTaskId) || generationStopping}
                      onClick={() => setEnableBrainstorming(!enableBrainstorming)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 ${
                        enableBrainstorming ? "bg-primary" : "bg-muted-foreground/30"
                      }`}
                    >
                      <span
                        className={`pointer-events-none block h-4 w-4 rounded-full bg-background shadow-md ring-0 transition-transform duration-300 ${
                          enableBrainstorming ? "translate-x-4" : "translate-x-0.5"
                        }`}
                      />
                    </button>
                    <div className="flex flex-col text-left">
                      <span className="text-[11px] font-semibold text-foreground select-none cursor-pointer" onClick={() => {
                        if (!isConnected && !generationTaskId && !generationStopping) {
                          setEnableBrainstorming(!enableBrainstorming)
                        }
                      }}>
                        开启多智能体脑暴 (Brainstorming)
                      </span>
                      <span className="text-[9px] text-muted-foreground">
                        大模型写作前，多角色 Agent 脑暴冲突与反转
                      </span>
                    </div>
                  </div>
                </div>
                <DialogFooter className="mt-2 flex gap-2 justify-end">
                  <DialogClose render={<Button variant="outline" size="sm" className="h-8 text-xs rounded-lg" />}>
                    取消
                  </DialogClose>
                  <DialogClose render={
                    <Button
                      size="sm"
                      onClick={handleGenerateChapterBatch}
                      disabled={isConnected || Boolean(generationTaskId) || generationStopping}
                      className="h-8 text-xs bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white shadow-md shadow-indigo-600/10 font-semibold rounded-lg"
                    />
                  }>
                    开始批量生成
                  </DialogClose>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* Batch Upload Input & Button */}
            <input
              type="file"
              ref={batchFileRef}
              className="hidden"
              multiple
              accept=".txt"
              onChange={handleBatchUploadChapters}
            />
            <Button
              size="sm"
              variant="outline"
              disabled={batchUploading}
              onClick={() => batchFileRef.current?.click()}
              className="h-8 text-xs bg-card/40 border-border/80 rounded-lg"
            >
              {batchUploading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Upload className="h-3 w-3 mr-1" />}
              导入章节
            </Button>
          </div>
        </div>
        <CardDescription className="text-xs">
          {completedChapters} 定稿 / {draftChapters} 草稿 / {pendingChapters} 待写
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0 flex-1 min-h-0">
        {!chapters?.length ? (
          <div className="px-4 pb-6 text-sm text-muted-foreground">尚未生成章节目录</div>
        ) : (
          <ScrollArea className="h-full pr-2">
            <div className="space-y-1 p-2">
              {chapters.map((chapter: Chapter) => (
                <button
                  key={chapter.chapter_number}
                  type="button"
                  onClick={() => {
                    setSelectedChapterNumber(chapter.chapter_number)
                    setHookChapterNum(chapter.chapter_number)
                  }}
                  className={`w-full rounded-xl px-3 py-2.5 text-left transition-all duration-200 border ${
                    selectedChapterNumber === chapter.chapter_number
                      ? "bg-primary/10 border-primary/20 text-primary font-semibold shadow-inner"
                      : "hover:bg-accent/40 border-transparent hover:translate-x-0.5"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] bg-secondary/80 px-1.5 py-0.5 rounded-md text-muted-foreground">
                      第{chapter.chapter_number}章
                    </span>
                    <Badge
                      variant={chapter.status === "final" ? "default" : chapter.status === "draft" ? "secondary" : "outline"}
                      className={`text-[10px] px-1.5 py-0 ${
                        chapter.status === "final"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : chapter.status === "draft"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                          : "bg-secondary text-muted-foreground"
                      }`}
                    >
                      {chapter.status === "final" ? "定稿" : chapter.status === "draft" ? "草稿" : "待写"}
                    </Badge>
                  </div>
                  <p className="mt-1.5 truncate text-sm leading-tight">{chapter.chapter_title || "未命名"}</p>
                  {chapter.word_count > 0 && <p className="mt-1 text-[10px] text-muted-foreground">{chapter.word_count} 字</p>}
                </button>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
