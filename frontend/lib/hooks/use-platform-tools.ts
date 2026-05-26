"use client"

import { useState } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import type { PlatformHookResult } from "@/lib/types"

export function usePlatformTools(projectId: string) {
  const [platformLoading, setPlatformLoading] = useState("")
  const [hookChapterNum, setHookChapterNum] = useState(1)
  
  const [titles, setTitles] = useState<string[]>([])
  const [blurbs, setBlurbs] = useState<string[]>([])
  const [chapterTitles, setChapterTitles] = useState<string[]>([])
  
  const [hookResult, setHookResult] = useState<PlatformHookResult | null>(null)
  const [chapterHookResult, setChapterHookResult] = useState<PlatformHookResult | null>(null)
  const [batchHookResult, setBatchHookResult] = useState<{ chapter_number: number, analysis: PlatformHookResult }[]>([])
  const [diagnosisResult, setDiagnosisResult] = useState<string>("")
  const [tagsResult, setTagsResult] = useState<any>(null)

  const wrapLoading = async (loadingKey: string, fn: () => Promise<void>) => {
    setPlatformLoading(loadingKey)
    try {
      await fn()
    } catch (error) {
      toast.error((error as Error).message || "操作失败")
    } finally {
      setPlatformLoading("")
    }
  }

  const handleGenTitles = () => wrapLoading("titles", async () => {
    const res = await api.platform.titles(projectId)
    setTitles(res.titles || [])
    toast.success("标题生成完成")
  })

  const handleGenBlurb = () => wrapLoading("blurb", async () => {
    const res = await api.platform.blurb(projectId)
    setBlurbs(res.blurbs || [])
    toast.success("文案生成完成")
  })

  const handleGenTags = () => wrapLoading("tags", async () => {
    const res = await api.platform.tags(projectId)
    setTagsResult(res.tags)
    toast.success("标签生成完成")
  })

  const handleGenSelectedChapterTitle = (chapterNum: number) => wrapLoading("workbenchTitle", async () => {
    const res = await api.platform.chapterTitle(projectId, chapterNum)
    setChapterTitles(res.titles || [])
  })

  const handleWorkbenchOpeningHook = (chapterNum: number = 1) => wrapLoading("workbenchOpening", async () => {
    const res = await api.platform.hookCheck(projectId, chapterNum)
    setHookResult(res.analysis || null)
  })

  const handleWorkbenchEndingHook = (chapterNum: number) => wrapLoading("workbenchEnding", async () => {
    const res = await api.platform.chapterHookCheck(projectId, chapterNum)
    setChapterHookResult(res.analysis || null)
  })

  const handleBatchHookCheck = () => wrapLoading("batch", async () => {
    const res = await api.platform.batchHookCheck(projectId)
    setBatchHookResult(res.chapters || [])
  })

  const handleDiagnoseChapter = (chapterNum: number) => wrapLoading("diagnosis", async () => {
    const res = await api.platform.diagnose(projectId, chapterNum)
    setDiagnosisResult(res.diagnosis || "")
  })

  return {
    platformLoading, setPlatformLoading,
    hookChapterNum, setHookChapterNum,
    titles, setTitles,
    blurbs, setBlurbs,
    chapterTitles, setChapterTitles,
    hookResult, setHookResult,
    chapterHookResult, setChapterHookResult,
    batchHookResult, setBatchHookResult,
    diagnosisResult, setDiagnosisResult,
    tagsResult, setTagsResult,
    handleGenTitles, handleGenBlurb, handleGenTags,
    handleGenSelectedChapterTitle, handleWorkbenchOpeningHook,
    handleWorkbenchEndingHook, handleDiagnoseChapter, handleBatchHookCheck,
    wrapLoading
  }
}
