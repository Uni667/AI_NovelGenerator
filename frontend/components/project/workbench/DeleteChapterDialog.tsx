"use client"

import React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2, Trash2 } from "lucide-react"
import { useDeleteChapter } from "@/lib/hooks/use-projects"
import { toast } from "sonner"
import type { Chapter } from "@/lib/types"

interface DeleteChapterDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  chapter: Chapter | null
  projectId: string
  /** Called after successful deletion — for navigation / state cleanup */
  onDeleted?: () => void
}

export function DeleteChapterDialog({
  open,
  onOpenChange,
  chapter,
  projectId,
  onDeleted,
}: DeleteChapterDialogProps) {
  const deleteMutation = useDeleteChapter(projectId)

  if (!chapter) return null

  const isFinal = chapter.status === "final"

  const handleDelete = async () => {
    if (isFinal) {
      toast.error("该章节已定稿，如需删除请先取消定稿或使用章节管理功能。")
      onOpenChange(false)
      return
    }

    try {
      await deleteMutation.mutateAsync(chapter.chapter_number)
      toast.success("草稿已删除")
      onOpenChange(false)
      onDeleted?.()
    } catch (e) {
      toast.error("删除失败，请稍后重试")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm bg-background/95 backdrop-blur-xl border-border/60 p-5 rounded-2xl">
        <DialogHeader>
          <DialogTitle className="text-base font-bold flex items-center gap-2 text-destructive">
            <Trash2 className="h-4.5 w-4.5" />
            确认删除草稿？
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground/80 mt-2 leading-relaxed">
            将清除第 <strong>{chapter.chapter_number}</strong> 章「{chapter.chapter_title || "未命名"}」的正文内容，章节状态将恢复为<strong>待写</strong>，大纲信息保留。<br /><strong className="text-destructive">此操作不可撤销。</strong>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4 flex gap-2 justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={deleteMutation.isPending}
            className="h-8 text-xs rounded-lg"
          >
            取消
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="h-8 text-xs rounded-lg"
          >
            {deleteMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            )}
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
