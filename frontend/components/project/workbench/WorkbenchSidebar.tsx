"use client"

import React, { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2, Upload, Sparkles, MoreVertical, Trash2, Copy, Edit3 } from "lucide-react"
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
import { DeleteChapterDialog } from "./DeleteChapterDialog"

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

  // --- More-menu state ---
  const [menuOpenChapter, setMenuOpenChapter] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Chapter | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  // Close menu on outside click
  useEffect(() => {
    if (menuOpenChapter === null) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenChapter(null)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [menuOpenChapter])

  // --- State helpers ---
  const completedChapters = chapters?.filter((c: Chapter) => c.status === "final").length || 0
  const draftChapters = chapters?.filter((c: Chapter) => c.status === "draft").length || 0
  const pendingChapters = chapters?.filter((c: Chapter) => c.status === "pending").length || 0

  // --- Handlers ---
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

  const handleGenerateSingleChapter = async (chapterNumber: number) => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      const url = `/api/v1/projects/${projectId}/generate/chapter/${chapterNumber}${enableBrainstorming ? "?enable_brainstorming=true" : ""}`
      setSelectedChapterNumber(chapterNumber)
      startTask("chapter", url, taskId)
      toast.success(`已开始生成第 ${chapterNumber} 章`)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  /** After deletion: navigate to sibling chapter or show empty state */
  const handleDeletedChapter = (deletedNum: number) => {
    setMenuOpenChapter(null)
    setDeleteTarget(null)

    if (!chapters) return

    // Find next / prev chapter numbers from the (stale) list
    const remaining = chapters
      .filter((c: Chapter) => c.chapter_number !== deletedNum)
      .sort((a, b) => a.chapter_number - b.chapter_number)

    if (remaining.length === 0) {
      // No chapters left — reset selection; the empty state will show
      setSelectedChapterNumber(0)
      return
    }

    // If the deleted chapter was the current one, navigate
    if (deletedNum === selectedChapterNumber) {
      // Try next chapter first
      const next = remaining.find((c) => c.chapter_number > deletedNum)
      if (next) {
        setSelectedChapterNumber(next.chapter_number)
        setHookChapterNum(next.chapter_number)
      } else {
        // Fall back to previous
        const prev = remaining[remaining.length - 1]
        setSelectedChapterNumber(prev.chapter_number)
        setHookChapterNum(prev.chapter_number)
      }
    }
  }

  const toggleMenu = (chapterNum: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpenChapter(menuOpenChapter === chapterNum ? null : chapterNum)
  }

  return (
    <Card className="glass-panel border-border/40 h-full flex flex-col hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
      <CardHeader className="pb-4 shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold text-gradient-primary w-fit">章节目录</CardTitle>
          <div className="flex items-center gap-2">
            {/* AI Batch Generate Dialog */}
            <Dialog>
              <DialogTrigger
                render={
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isConnected || Boolean(generationTaskId) || generationStopping}
                    className="h-8 text-xs bg-gradient-to-r from-violet-600/10 to-indigo-600/10 border-violet-500/30 hover:border-violet-400/60 hover:bg-violet-500/10 text-violet-400 rounded-lg"
                  >
                    <Sparkles className="h-3 w-3 mr-1" />
                    批量生成
                  </Button>
                }
              />
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
          <div className="px-4 pb-6 text-sm text-muted-foreground">暂无章节，请新建或导入章节。</div>
        ) : (
          <ScrollArea className="h-full pr-2">
            <div className="space-y-1 p-2">
              {chapters.map((chapter: Chapter) => (
                <div
                  key={chapter.chapter_number}
                  className={`group/chapter w-full rounded-lg text-left transition-all duration-200 border flex items-stretch ${
                    selectedChapterNumber === chapter.chapter_number
                      ? "bg-primary/10 border-primary/20"
                      : "hover:bg-accent/30 border-transparent"
                  }`}
                >
                  {/* Main click target — select chapter */}
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedChapterNumber(chapter.chapter_number)
                      setHookChapterNum(chapter.chapter_number)
                      setMenuOpenChapter(null)
                    }}
                    className="flex-1 min-w-0 px-2.5 py-1.5"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`font-mono text-[9px] px-1 rounded ${
                        selectedChapterNumber === chapter.chapter_number
                          ? "bg-primary/20 text-primary"
                          : "bg-secondary/80 text-muted-foreground"
                      }`}>
                        {chapter.chapter_number}
                      </span>
                      <span className="flex-1 truncate text-xs font-medium leading-tight">
                        {chapter.chapter_title || "未命名"}
                      </span>
                      <Badge
                        variant={chapter.status === "final" ? "default" : chapter.status === "draft" ? "secondary" : "outline"}
                        className={`text-[8px] px-1 py-0 ${
                          chapter.status === "final"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : chapter.status === "draft"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-secondary text-muted-foreground"
                        }`}
                      >
                        {chapter.status === "final" ? "定" : chapter.status === "draft" ? "草" : "待"}
                      </Badge>
                      {chapter.word_count > 0 && (
                        <span className="text-[8px] text-muted-foreground tabular-nums">{chapter.word_count}</span>
                      )}
                    </div>
                  </button>

                  {/* More-actions button (three dots) */}
                  <div className="relative shrink-0 flex items-center">
                    <button
                      type="button"
                      onClick={(e) => toggleMenu(chapter.chapter_number, e)}
                      className="flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground/40 hover:text-foreground hover:bg-accent/40 transition-colors"
                      title="更多操作"
                    >
                      <MoreVertical className="h-3.5 w-3.5" />
                    </button>

                    {/* Dropdown menu */}
                    {menuOpenChapter === chapter.chapter_number && (
                      <div
                        ref={menuRef}
                        className="absolute right-0 top-full z-50 mt-1 min-w-[140px] rounded-lg border border-border/50 bg-popover backdrop-blur-xl shadow-xl py-1 animate-in fade-in zoom-in-95 duration-150"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-foreground hover:bg-accent/40 transition-colors"
                          onClick={() => {
                            toast.info("章节编辑功能开发中")
                            setMenuOpenChapter(null)
                          }}
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                          编辑信息
                        </button>
                        <button
                          type="button"
                          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-foreground hover:bg-accent/40 transition-colors"
                          onClick={() => {
                            toast.info("复制章节功能开发中")
                            setMenuOpenChapter(null)
                          }}
                        >
                          <Copy className="h-3.5 w-3.5" />
                          复制章节
                        </button>
                        <div className="h-px bg-border/30 my-1 mx-2" />
                        <button
                          type="button"
                          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 transition-colors"
                          onClick={() => {
                            setDeleteTarget(chapter)
                            setMenuOpenChapter(null)
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          删除草稿
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Quick-generate button (for non-final chapters) */}
                  {chapter.status !== "final" && (
                    <button
                      type="button"
                      title={`生成第${chapter.chapter_number}章`}
                      disabled={isConnected || Boolean(generationTaskId) || generationStopping}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleGenerateSingleChapter(chapter.chapter_number)
                        setMenuOpenChapter(null)
                      }}
                      className="shrink-0 flex items-center justify-center w-7 rounded-r-lg text-violet-400/60 hover:text-violet-300 hover:bg-violet-500/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed opacity-0 group-hover/chapter:opacity-100"
                    >
                      <Sparkles className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>

      {/* Delete confirmation dialog */}
      <DeleteChapterDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        chapter={deleteTarget}
        projectId={projectId}
        onDeleted={() => {
          if (deleteTarget) {
            handleDeletedChapter(deleteTarget.chapter_number)
          }
        }}
      />
    </Card>
  )
}
