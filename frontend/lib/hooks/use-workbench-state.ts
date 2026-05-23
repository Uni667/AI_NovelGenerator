"use client"

import { useState } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import type { Chapter } from "@/lib/types"

export function useWorkbenchState(projectId: string) {
  const [selectedChapterNumber, setSelectedChapterNumber] = useState(1)
  const [chapterEditorContent, setChapterEditorContent] = useState("")
  const [chapterEditorLoading, setChapterEditorLoading] = useState(false)
  const [chapterEditorSaving, setChapterEditorSaving] = useState(false)
  const [activeChapterMeta, setActiveChapterMeta] = useState<Chapter | null>(null)

  const loadWorkbenchChapter = async (num: number) => {
    setChapterEditorLoading(true)
    try {
      const res = await api.chapters.get(projectId, num)
      setChapterEditorContent(res.content || "")
      setActiveChapterMeta(res.meta || null)
    } catch (error) {
      toast.error((error as Error).message || "获取章节内容失败")
      setChapterEditorContent("")
      setActiveChapterMeta(null)
    } finally {
      setChapterEditorLoading(false)
    }
  }

  const saveWorkbenchChapter = async () => {
    setChapterEditorSaving(true)
    try {
      await api.chapters.update(projectId, selectedChapterNumber, { content: chapterEditorContent })
      toast.success("保存成功")
    } catch (error) {
      toast.error((error as Error).message || "保存草稿失败")
    } finally {
      setChapterEditorSaving(false)
    }
  }

  return {
    selectedChapterNumber, setSelectedChapterNumber,
    chapterEditorContent, setChapterEditorContent,
    chapterEditorLoading,
    chapterEditorSaving,
    activeChapterMeta, setActiveChapterMeta,
    loadWorkbenchChapter,
    saveWorkbenchChapter
  }
}
