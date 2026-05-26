"use client"

import { useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import type { Chapter } from "@/lib/types"

export function useWorkbenchState(projectId: string) {
  const [selectedChapterNumber, setSelectedChapterNumber] = useState(1)
  const [chapterEditorContent, setChapterEditorContent] = useState("")
  const [chapterEditorLoading, setChapterEditorLoading] = useState(false)
  const [chapterEditorSaving, setChapterEditorSaving] = useState(false)
  const [activeChapterMeta, setActiveChapterMeta] = useState<Chapter | null>(null)

  const loadWorkbenchChapter = useCallback(async (num: number) => {
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
  }, [projectId])

  const saveWorkbenchChapter = useCallback(async (): Promise<Chapter | null> => {
    setChapterEditorSaving(true)
    try {
      const res = await api.chapters.update(projectId, selectedChapterNumber, { content: chapterEditorContent })
      const meta = res.meta || null
      if (meta) {
        setActiveChapterMeta(meta)
      }
      toast.success("保存成功")
      return meta
    } catch (error) {
      toast.error((error as Error).message || "保存草稿失败")
      return null
    } finally {
      setChapterEditorSaving(false)
    }
  }, [projectId, selectedChapterNumber, chapterEditorContent])

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
