"use client"

import { useParams, useRouter } from "next/navigation"
import { useProject, useProjectConfig, useChapters, useUpdateProjectConfig } from "@/lib/hooks/use-projects"
import { useSSE } from "@/lib/hooks/use-sse"
import { api } from "@/lib/api-client"
import { PLATFORM_CONFIG, PLATFORMS, ProjectFile, TASK_STATUS_LABELS, TASK_TYPE_LABELS } from "@/lib/types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useState, useEffect, useRef, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Play, FileText, Upload, Trash2, CheckCircle, AlertCircle, Loader2, Users, UserPlus, FileDown, Wand2, BookMarked, Target, Tag, FileEdit, RefreshCw, Copy, Save, BookOpen, MessageSquare, Sparkles, Eye, ListChecks, Gauge, PlusCircle, Ban, GitBranch, Swords, Clock } from "lucide-react"
import RelationshipManager from "@/components/character/RelationshipManager"
import ConflictManager from "@/components/character/ConflictManager"
import AppearanceTimeline from "@/components/character/AppearanceTimeline"
import { ArchitectureStatusCard } from "@/components/files/ArchitectureStatusCard"
import { OutlineStatusCard } from "@/components/files/OutlineStatusCard"
import { FileImportDialog } from "@/components/files/FileImportDialog"

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

const GENERATION_STEP_META: Record<string, { label: string; description: string }> = {
  core_seed: {
    label: "核心种子",
    description: "确定小说的核心卖点、主角欲望、主线冲突和读者情绪承诺",
  },
  character: {
    label: "角色架构",
    description: "设计角色总览、人物详卡、关系冲突网、出场路线和人设约束",
  },
  character_state: {
    label: "角色状态表",
    description: "把角色当前身份、目标、关系和秘密整理成后续章节可追踪的状态",
  },
  world: {
    label: "世界观",
    description: "确定故事规则、势力结构、资源体系和主角行动边界",
  },
  plot: {
    label: "三幕式情节架构",
    description: "把整本书拆成开局立钩子、中段冲突升级、后段爆发收束三段主线",
  },
  global_summary_init: {
    label: "初始全局摘要",
    description: "在架构完成后生成整本书的初始全局摘要，作为后续写作的连续性底稿",
  },
  plot_arcs_init: {
    label: "伏笔暗线台账",
    description: "在架构完成后建立伏笔、秘密、道具和反转的初始台账",
  },
  summary_update: {
    label: "全局摘要更新",
    description: "章节定稿后把新增事件、角色变化和已发生进展同步进摘要",
  },
  character_state_update: {
    label: "角色状态更新",
    description: "章节定稿后同步更新角色身份、关系、秘密和触发事件",
  },
  plot_arcs_update: {
    label: "伏笔暗线更新",
    description: "章节定稿后更新伏笔状态、回收计划和新增暗线",
  },
  all: {
    label: "架构汇总",
    description: "整合核心种子、人物、世界观和三幕式情节架构",
  },
  blueprint: {
    label: "章节目录",
    description: "把全书架构拆成章节标题、章节作用和每章推进目标",
  },
  build_prompt: {
    label: "章节提示词",
    description: "根据架构、目录和上下文构建当前章节写作提示",
  },
  draft: {
    label: "章节草稿",
    description: "生成当前章节正文草稿",
  },
  finalize: {
    label: "章节定稿",
    description: "定稿章节，并更新全局摘要、角色状态、伏笔暗线和后续上下文",
  },
  batch: {
    label: "批量章节生成",
    description: "按顺序生成多章草稿",
  },
}

const generationStepMeta = (step?: string) => {
  if (!step) return { label: "生成步骤", description: "正在执行生成流程" }
  return GENERATION_STEP_META[step] || { label: step, description: "生成流程中的内部步骤" }
}

const CHARACTER_STATUS_OPTIONS = [
  { value: "appeared", label: "已出现" },
  { value: "planned", label: "计划登场" },
  { value: "suggested", label: "AI 建议" },
] as const

const CHARACTER_SOURCE_OPTIONS = [
  { value: "user", label: "我设定" },
  { value: "ai", label: "AI 生成" },
] as const

const characterStatusLabel = (status?: string) => {
  return CHARACTER_STATUS_OPTIONS.find((item) => item.value === status)?.label || "已出现"
}

const characterSourceLabel = (source?: string) => {
  return CHARACTER_SOURCE_OPTIONS.find((item) => item.value === source)?.label || "我设定"
}

const createClientTaskId = () => {
  try {
    return crypto.randomUUID().replace(/-/g, "")
  } catch {
    return `${Date.now()}${Math.random().toString(16).slice(2)}`
  }
}

const formatFileSize = (size?: number) => {
  if (!size || size <= 0) return "0 B"
  const units = ["B", "KB", "MB", "GB"]
  let value = size
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

export default function ProjectDashboard() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { data: project, isLoading } = useProject(id)
  const { data: config } = useProjectConfig(id)
  const { data: chapters } = useChapters(id)
  const updateConfig = useUpdateProjectConfig(id)
  const { events, isConnected, error: sseError, connect } = useSSE()
  const queryClient = useQueryClient()
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const [activeTab, setActiveTab] = useState("overview")
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [characters, setCharacters] = useState<any[]>([])
  const [charDialogOpen, setCharDialogOpen] = useState(false)
  const [editChar, setEditChar] = useState<any>(null)
  const [charName, setCharName] = useState("")
  const [charDesc, setCharDesc] = useState("")
  const [charStatus, setCharStatus] = useState("planned")
  const [charSource, setCharSource] = useState("user")
  const [charFirstChapter, setCharFirstChapter] = useState<number | "">("")
  const [deleteCharTarget, setDeleteCharTarget] = useState<number | null>(null)
  const [characterSuggestions, setCharacterSuggestions] = useState<any[]>([])
  const [characterLoading, setCharacterLoading] = useState("")
  const [dashboardSummary, setDashboardSummary] = useState<any>(null)

  // 平台工具状态
  const [titles, setTitles] = useState<string[]>([])
  const [blurbs, setBlurbs] = useState<string[]>([])
  const [hookResult, setHookResult] = useState<any>(null)
  const [batchHookResult, setBatchHookResult] = useState<any[]>([])
  const [tagsResult, setTagsResult] = useState<any>(null)
  const [chapterTitles, setChapterTitles] = useState<string[]>([])
  const [platformLoading, setPlatformLoading] = useState("")
  const [hookChapterNum, setHookChapterNum] = useState(1)
  const [llmConfigs, setLLMConfigs] = useState<Record<string, any>>({})
  const [embConfigs, setEmbConfigs] = useState<Record<string, any>>({})
  const [selectedOutputFile, setSelectedOutputFile] = useState<(typeof GENERATED_FILES)[number]["filename"]>(GENERATED_FILES[0].filename)
  const [outputFileContent, setOutputFileContent] = useState("")
  const [outputFileLoading, setOutputFileLoading] = useState(false)
  const [outputFileError, setOutputFileError] = useState("")
  const [deleteOutputDialogOpen, setDeleteOutputDialogOpen] = useState(false)
  const [generationChapterCount, setGenerationChapterCount] = useState(0)
  const [generationWordCount, setGenerationWordCount] = useState(3000)
  const [selectedChapterNumber, setSelectedChapterNumber] = useState(1)
  const [batchChapterCount, setBatchChapterCount] = useState(1)
  const [chapterEditorContent, setChapterEditorContent] = useState("")
  const [chapterEditorMeta, setChapterEditorMeta] = useState<any>(null)
  const [chapterEditorLoading, setChapterEditorLoading] = useState(false)
  const [chapterEditorSaving, setChapterEditorSaving] = useState(false)
  const [readerChapterNum, setReaderChapterNum] = useState(1)
  const [chapterHookResult, setChapterHookResult] = useState<any>(null)
  const [sseAction, setSseAction] = useState<"architecture" | "blueprint" | "chapter" | "chapterBatch" | "finalize" | null>(null)
  const [generationTaskId, setGenerationTaskId] = useState<string | null>(null)
  const [generationTaskLabel, setGenerationTaskLabel] = useState("")
  const [generationStopping, setGenerationStopping] = useState(false)
  const [knowledgeFiles, setKnowledgeFiles] = useState<any[]>([])
  const [knowledgeLoading, setKnowledgeLoading] = useState(false)
  const [knowledgeError, setKnowledgeError] = useState("")
  const [knowledgeDeleteTarget, setKnowledgeDeleteTarget] = useState<any>(null)
  const [characterImportPreviewOpen, setCharacterImportPreviewOpen] = useState(false)
  const [characterImportCandidates, setCharacterImportCandidates] = useState<any[]>([])
  const [characterImportSummary, setCharacterImportSummary] = useState<any>({})
  const [characterImportSelectedIds, setCharacterImportSelectedIds] = useState<string[]>([])
  const [characterImportLoading, setCharacterImportLoading] = useState(false)
  const [characterImportConfirming, setCharacterImportConfirming] = useState(false)

  // ── 架构/目录状态 ──
  const [architectureFile, setArchitectureFile] = useState<ProjectFile | null>(null)
  const [outlineFile, setOutlineFile] = useState<ProjectFile | null>(null)
  const [archOutlineLoading, setArchOutlineLoading] = useState(true)
  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const [importDialogFileType, setImportDialogFileType] = useState<"architecture" | "outline">("architecture")

  const loadArchitectureAndOutline = useCallback(async () => {
    if (!id) return
    setArchOutlineLoading(true)
    const [arch, outline] = await Promise.all([
      api.projectFiles.getCurrentArchitecture(id),
      api.projectFiles.getCurrentOutline(id),
    ])
    setArchitectureFile(arch)
    setOutlineFile(outline)
    setArchOutlineLoading(false)
  }, [id])

  useEffect(() => {
    loadArchitectureAndOutline()
  }, [loadArchitectureAndOutline])

  // ── 生成前检查 ──
  const checkArchitecture = (): boolean => {
    if (!architectureFile) {
      toast.error("请先生成或导入小说架构")
      return false
    }
    return true
  }

  const checkOutline = (): boolean => {
    if (!architectureFile) {
      toast.error("请先生成或导入小说架构")
      return false
    }
    if (!outlineFile) {
      toast.error("请先生成或导入章节目录")
      return false
    }
    return true
  }

  const outputFileRequestId = useRef(0)
  const autoOpenFilesAfterDoneRef = useRef(false)
  const handledGenerationTaskIdRef = useRef<string | null>(null)

  const usageLabel = (usage: string) => {
    const map: Record<string, string> = { general: "通用", architecture: "架构生成", outline: "章节目录", draft: "章节草稿", finalize: "定稿", review: "一致性审校", platform: "平台工具" }
    return map[usage] || "通用"
  }

  useEffect(() => {
    api.config.llmList().then(setLLMConfigs).catch(() => {})
    api.config.embList().then(setEmbConfigs).catch(() => {})
  }, [])

  useEffect(() => {
    if (!config) return
    setGenerationChapterCount(config.num_chapters || 0)
    setGenerationWordCount(config.word_number || 3000)
  }, [config])

  useEffect(() => {
    if (!chapters?.length) return
    const exists = chapters.some((chapter: any) => chapter.chapter_number === selectedChapterNumber)
    if (!exists) {
      setSelectedChapterNumber(chapters[0].chapter_number)
      setReaderChapterNum(chapters[0].chapter_number)
      setHookChapterNum(chapters[0].chapter_number)
    }
  }, [chapters, selectedChapterNumber])

  const lastPartial = events.filter(e => e.type === "partial").pop()
  const lastError = events.filter(e => e.type === "error").pop()
  const lastCancelled = events.filter(e => e.type === "cancelled").pop()
  const lastDone = events.filter(e => e.type === "done").pop()
  const hasError = Boolean(lastError)

  const debouncedUpdate = (data: Record<string, any>) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => updateConfig.mutate(data), 500)
  }

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [])

  const loadCharacters = useCallback(async () => {
    try { setCharacters(await api.characters.list(id)) } catch { /* ignore */ }
  }, [id])

  const loadDashboard = useCallback(async () => {
    try { setDashboardSummary((await api.characters.dashboard(id)).summary) } catch { /* ignore */ }
  }, [id])

  useEffect(() => {
    if (activeTab === "characters") { loadCharacters(); loadDashboard() }
  }, [activeTab, id, loadCharacters, loadDashboard])

  const handleCreateCharacter = async () => {
    if (!charName.trim()) return
    await api.characters.create(id, {
      name: charName,
      description: charDesc,
      status: charStatus,
      source: charSource,
      first_appearance_chapter: charFirstChapter === "" ? null : Number(charFirstChapter),
    })
    toast.success("角色已创建")
    setCharDialogOpen(false)
    setCharName("")
    setCharDesc("")
    setCharFirstChapter("")
    loadCharacters()
  }

  const handleUpdateCharacter = async () => {
    if (!editChar || !charName.trim()) return
    await api.characters.update(id, editChar.id, {
      name: charName,
      description: charDesc,
      status: charStatus,
      source: charSource,
      first_appearance_chapter: charFirstChapter === "" ? null : Number(charFirstChapter),
    })
    toast.success("角色已更新")
    setEditChar(null)
    setCharDialogOpen(false)
    setCharFirstChapter("")
    loadCharacters()
  }

  const handleDeleteCharacter = async () => {
    if (deleteCharTarget === null) return
    await api.characters.delete(id, deleteCharTarget)
    toast.success("角色已删除")
    setDeleteCharTarget(null)
    loadCharacters()
  }

  const handleImportCharacters = async () => {
    setCharacterImportLoading(true)
    try {
      const result = await api.characters.importPreview(id)
      const candidates = result.candidates || []
      setCharacterImportSummary(result.summary || {})
      setCharacterImportCandidates(candidates)
      setCharacterImportSelectedIds(candidates.filter((candidate: any) => candidate.decision !== "reject").map((candidate: any) => candidate.candidate_id))
      setCharacterImportPreviewOpen(true)
    } catch (error: any) {
      toast.error(error?.message || "角色导入预览失败")
    } finally {
      setCharacterImportLoading(false)
    }
  }

  const handleConfirmCharacterImport = async () => {
    if (characterImportSelectedIds.length === 0) {
      toast.error("请至少选择一个候选角色")
      return
    }
    setCharacterImportConfirming(true)
    try {
      const result = await api.characters.importFromState(id, { selected_candidate_ids: characterImportSelectedIds })
      toast.success(result.message || "导入完成")
      setCharacterImportPreviewOpen(false)
      setCharacterImportCandidates([])
      setCharacterImportSelectedIds([])
      setCharacterImportSummary({})
      loadCharacters()
    } catch (error: any) {
      toast.error(error?.message || "角色导入失败")
    } finally {
      setCharacterImportConfirming(false)
    }
  }

  const selectCharacterImportCandidates = (mode: "recommended" | "all" | "none") => {
    if (mode === "none") {
      setCharacterImportSelectedIds([])
      return
    }
    if (mode === "all") {
      setCharacterImportSelectedIds(characterImportCandidates.map((candidate: any) => candidate.candidate_id))
      return
    }
    setCharacterImportSelectedIds(
      characterImportCandidates
        .filter((candidate: any) => candidate.decision !== "reject")
        .map((candidate: any) => candidate.candidate_id),
    )
  }

  const toggleCharacterImportCandidate = (candidateId: string) => {
    setCharacterImportSelectedIds((current) => (
      current.includes(candidateId)
        ? current.filter((item) => item !== candidateId)
        : [...current, candidateId]
    ))
  }

  const handleSuggestCharacters = async () => {
    setCharacterLoading("suggest")
    try {
      const result = await api.characters.suggest(id)
      setCharacterSuggestions(result.characters || [])
      toast.success(`已生成 ${result.characters?.length || 0} 个角色建议`)
    } catch (error: any) {
      toast.error(error?.message || "角色建议生成失败")
    } finally {
      setCharacterLoading("")
    }
  }

  const handleAcceptCharacterSuggestion = async (suggestion: any) => {
    await api.characters.create(id, {
      name: suggestion.name,
      description: suggestion.description,
      status: "planned",
      source: "ai",
      first_appearance_chapter: suggestion.first_appearance_chapter ?? null,
    })
    toast.success("已加入计划登场")
    setCharacterSuggestions((items) => items.filter((item) => item.name !== suggestion.name))
    loadCharacters()
  }

  const openEditDialog = (char: any) => {
    setEditChar(char)
    setCharName(char.name)
    setCharDesc(char.description || "")
    setCharStatus(char.status || "appeared")
    setCharSource(char.source || "user")
    setCharFirstChapter(char.first_appearance_chapter ?? "")
    setCharDialogOpen(true)
  }

  const openCreateDialog = (status = "planned", source = "user") => {
    setEditChar(null)
    setCharName("")
    setCharDesc("")
    setCharStatus(status)
    setCharSource(source)
    setCharFirstChapter("")
    setCharDialogOpen(true)
  }

  const withLoading = async (key: string, fn: () => Promise<void>) => {
    setPlatformLoading(key)
    try { await fn() } catch (e: any) { toast.error(e.message || "操作失败") }
    finally { setPlatformLoading("") }
  }

  const handleGenTitles = () => withLoading("titles", async () => {
    const res = await api.platform.titles(id)
    setTitles(res.titles)
  })

  const handleGenBlurb = () => withLoading("blurb", async () => {
    const res = await api.platform.blurb(id)
    setBlurbs(res.blurbs)
  })

  const handleHookCheck = () => withLoading("hook", async () => {
    const res = await api.platform.hookCheck(id, hookChapterNum)
    setHookResult(res.analysis)
  })

  const handleBatchHookCheck = () => withLoading("batch", async () => {
    const res = await api.platform.batchHookCheck(id)
    setBatchHookResult(res.chapters || [])
  })

  const handleGenTags = () => withLoading("tags", async () => {
    const res = await api.platform.tags(id)
    setTagsResult(res.tags)
  })

  const handleGenChapterTitle = () => withLoading("chapterTitle", async () => {
    const res = await api.platform.chapterTitle(id, hookChapterNum)
    setChapterTitles(res.titles)
  })

  const saveGenerationTargets = useCallback(async () => {
    const updates: Record<string, number> = {}
    if (generationChapterCount && generationChapterCount !== config?.num_chapters) {
      updates.num_chapters = generationChapterCount
    }
    if (generationWordCount && generationWordCount !== config?.word_number) {
      updates.word_number = generationWordCount
    }
    if (Object.keys(updates).length > 0) {
      await updateConfig.mutateAsync(updates)
    }
  }, [config?.num_chapters, config?.word_number, generationChapterCount, generationWordCount, updateConfig])

  const handleApplyGenerationTargets = async () => {
    await saveGenerationTargets()
    toast.success("生成控制已更新")
  }

  const buildGenerationStreamUrl = useCallback((path: string, taskId: string) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    const url = new URL(path, base)
    url.searchParams.set("task_id", taskId)
    url.searchParams.set("t", `${Date.now()}`)
    return url.toString()
  }, [])

  const openGenerationStream = useCallback((
    kind: "architecture" | "blueprint" | "chapter" | "chapterBatch" | "finalize",
    label: string,
    path: string,
    targetTab: "generation" | "workbench",
    preferredFile?: (typeof GENERATED_FILES)[number]["filename"],
  ) => {
    if (generationTaskId || isConnected || generationStopping) {
      toast.error("当前已有生成任务正在运行")
      return false
    }

    handledGenerationTaskIdRef.current = null
    const taskId = createClientTaskId()
    setGenerationTaskId(taskId)
    setGenerationTaskLabel(label)
    setGenerationStopping(false)
    setSseAction(kind)
    if (kind === "architecture" || kind === "blueprint") {
      autoOpenFilesAfterDoneRef.current = false
    }
    if (preferredFile) {
      setSelectedOutputFile(preferredFile)
    }
    setActiveTab(targetTab)
    connect(buildGenerationStreamUrl(path, taskId))
    return true
  }, [buildGenerationStreamUrl, connect, generationStopping, generationTaskId, isConnected])

  const clearGenerationState = useCallback(() => {
    handledGenerationTaskIdRef.current = null
    setGenerationTaskId(null)
    setGenerationTaskLabel("")
    setGenerationStopping(false)
  }, [])

  const refreshKnowledgeFiles = useCallback(async () => {
    setKnowledgeLoading(true)
    setKnowledgeError("")
    try {
      const files = await api.knowledge.list(id)
      setKnowledgeFiles(files || [])
    } catch (error: any) {
      setKnowledgeFiles([])
      setKnowledgeError(error?.message || "加载知识库文件失败")
    } finally {
      setKnowledgeLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (activeTab === "knowledge") {
      void refreshKnowledgeFiles()
    }
  }, [activeTab, refreshKnowledgeFiles])

  const loadWorkbenchChapter = useCallback(async (chapterNumber: number) => {
    setChapterEditorLoading(true)
    try {
      const data = await api.chapters.get(id, chapterNumber)
      setChapterEditorContent(data.content || "")
      setChapterEditorMeta(data.meta || null)
    } catch (error: any) {
      toast.error(error?.message || "章节内容读取失败")
      setChapterEditorContent("")
      setChapterEditorMeta(null)
    } finally {
      setChapterEditorLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (activeTab === "workbench") {
      loadWorkbenchChapter(selectedChapterNumber)
    }
  }, [activeTab, loadWorkbenchChapter, selectedChapterNumber])

  const handleSaveWorkbenchChapter = async () => {
    if (!chapterEditorContent.trim()) {
      toast.error("章节内容不能为空")
      return
    }
    setChapterEditorSaving(true)
    try {
      const result = await api.chapters.update(id, selectedChapterNumber, { content: chapterEditorContent })
      setChapterEditorMeta(result.meta)
      await queryClient.invalidateQueries({ queryKey: ["chapters", id] })
      toast.success("章节草稿已保存")
    } catch (error: any) {
      toast.error(error?.message || "保存失败")
    } finally {
      setChapterEditorSaving(false)
    }
  }

  const handleGenerateWorkbenchChapter = async () => {
    if (!checkOutline()) return
    try {
      await saveGenerationTargets()
      openGenerationStream(
        "chapter",
        `第 ${selectedChapterNumber} 章草稿`,
        `/api/v1/projects/${id}/generate/chapter/${selectedChapterNumber}`,
        "workbench",
      )
    } catch (error: any) {
      toast.error(error?.message || "章节生成启动失败")
    }
  }

  const handleGenerateChapterBatch = async () => {
    if (!checkOutline()) return
    try {
      await saveGenerationTargets()
      openGenerationStream(
        "chapterBatch",
        `批量生成 ${batchChapterCount} 章`,
        `/api/v1/projects/${id}/generate/chapters?start_chapter=${selectedChapterNumber}&count=${batchChapterCount}`,
        "workbench",
      )
    } catch (error: any) {
      toast.error(error?.message || "批量生成启动失败")
    }
  }

  const handleFinalizeWorkbenchChapter = () => {
    if (!chapterEditorContent.trim()) {
      toast.error("章节内容不能为空")
      return
    }
    if (generationTaskId || isConnected || generationStopping) {
      toast.error("当前已有生成任务正在运行")
      return
    }
    api.chapters.update(id, selectedChapterNumber, { content: chapterEditorContent })
      .then((result) => {
        setChapterEditorMeta(result.meta)
        return queryClient.invalidateQueries({ queryKey: ["chapters", id] })
      })
      .then(() => {
        openGenerationStream(
          "finalize",
          `第 ${selectedChapterNumber} 章定稿`,
          `/api/v1/projects/${id}/generate/finalize/${selectedChapterNumber}`,
          "workbench",
        )
      })
      .catch((error: any) => {
        toast.error(error?.message || "定稿前保存失败")
      })
  }

  const handleWorkbenchOpeningHook = () => withLoading("workbenchOpening", async () => {
    const res = await api.platform.hookCheck(id, selectedChapterNumber)
    setHookResult(res.analysis)
    setReaderChapterNum(selectedChapterNumber)
  })

  const handleWorkbenchEndingHook = () => withLoading("workbenchEnding", async () => {
    const res = await api.platform.chapterHookCheck(id, selectedChapterNumber)
    setChapterHookResult(res.analysis)
    setReaderChapterNum(selectedChapterNumber)
  })

  const handleGenSelectedChapterTitle = () => withLoading("workbenchTitle", async () => {
    const res = await api.platform.chapterTitle(id, selectedChapterNumber)
    setChapterTitles(res.titles)
  })

  const handleReaderOpeningCheck = () => withLoading("readerOpening", async () => {
    const res = await api.platform.hookCheck(id, readerChapterNum)
    setHookResult(res.analysis)
  })

  const handleReaderEndingCheck = () => withLoading("readerEnding", async () => {
    const res = await api.platform.chapterHookCheck(id, readerChapterNum)
    setChapterHookResult(res.analysis)
  })

  const loadOutputFile = useCallback(async (filename: string) => {
    const requestId = ++outputFileRequestId.current
    setOutputFileLoading(true)
    setOutputFileError("")
    try {
      const content = await api.files.get(id, filename)
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
  }, [id])

  useEffect(() => {
    if (activeTab === "files") {
      loadOutputFile(selectedOutputFile)
    }
  }, [activeTab, selectedOutputFile, loadOutputFile])

  // 生成超时保护：如果 10 分钟没有新事件且连接断开，自动清理卡死状态
  const generationStartTimeRef = useRef(0)
  useEffect(() => {
    if (generationTaskId && isConnected && generationStartTimeRef.current === 0) {
      generationStartTimeRef.current = Date.now()
    }
    if (!generationTaskId) {
      generationStartTimeRef.current = 0
    }
  }, [generationTaskId, isConnected])

  useEffect(() => {
    if (!generationTaskId || !isConnected || generationStartTimeRef.current === 0) return
    const elapsed = Date.now() - generationStartTimeRef.current
    if (elapsed < 10 * 60_000) return

    // super slow generation — just treat as stuck
    toast.error("生成超时，连接已断开，请重试")
    clearGenerationState()
  }, [generationTaskId, isConnected, clearGenerationState, events])

  useEffect(() => {
    const terminalEvent = lastCancelled || lastDone || lastError
    const taskId = terminalEvent?.data?.task_id

    // SSE 连接级错误（如网络中断），利用 sseError 兜底
    if (!terminalEvent && sseError && generationTaskId) {
      toast.error(sseError)
      clearGenerationState()
      return
    }

    if (!terminalEvent || !taskId) return
    if (handledGenerationTaskIdRef.current === taskId) return
    if (generationTaskId && taskId !== generationTaskId) return

    handledGenerationTaskIdRef.current = taskId
    setGenerationStopping(false)
    setGenerationTaskId(null)
    setGenerationTaskLabel("")

    if (lastCancelled?.data?.task_id === taskId) {
      toast.info(lastCancelled?.data?.message || "生成任务已取消")
      return
    }

    if (lastError?.data?.task_id === taskId) {
      toast.error(lastError?.data?.message || "生成任务失败")
      return
    }

    // 架构/目录生成完成后刷新状态
    if (sseAction === "architecture" || sseAction === "blueprint") {
      loadArchitectureAndOutline()
      queryClient.invalidateQueries({ queryKey: ["chapters", id] })
    }

    if (activeTab === "generation" && (sseAction === "architecture" || sseAction === "blueprint") && !autoOpenFilesAfterDoneRef.current) {
      autoOpenFilesAfterDoneRef.current = true
      setActiveTab("files")
    }

    if (sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") {
      loadWorkbenchChapter(selectedChapterNumber)
      queryClient.invalidateQueries({ queryKey: ["chapters", id] })
    }
  }, [activeTab, generationTaskId, id, lastCancelled, lastDone, lastError, sseError, loadWorkbenchChapter, queryClient, selectedChapterNumber, sseAction, clearGenerationState])

  const handleCopyOutput = async () => {
    if (!outputFileContent) return
    try {
      await navigator.clipboard.writeText(outputFileContent)
      toast.success("已复制到剪贴板")
    } catch {
      toast.error("复制失败")
    }
  }

  const handleDownloadOutput = async () => {
    try {
      const content = outputFileContent || await api.files.get(id, selectedOutputFile)
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = selectedOutputFile
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      toast.success("已下载")
    } catch (error: any) {
      toast.error(error?.message || "下载失败")
    }
  }

  const handleDeleteOutputFile = async () => {
    try {
      const result = await api.files.delete(id, selectedOutputFile)
      toast.success(result.message || "文件已删除")
      setDeleteOutputDialogOpen(false)
      setOutputFileContent("")
      setOutputFileError(`文件已删除: ${selectedOutputFile}`)
      if (selectedOutputFile === "Novel_directory.txt") {
        setChapterEditorContent("")
        setChapterEditorMeta(null)
        await queryClient.invalidateQueries({ queryKey: ["chapters", id] })
      }
    } catch (error: any) {
      toast.error(error?.message || "删除失败")
    }
  }

  const handleGenerateArchitecture = async () => {
    try {
      await saveGenerationTargets()
      openGenerationStream(
        "architecture",
        "生成架构",
        `/api/v1/projects/${id}/generate/architecture`,
        "generation",
        "Novel_architecture.txt",
      )
    } catch (error: any) {
      toast.error(error?.message || "架构生成启动失败")
    }
  }

  const handleGenerateBlueprint = async () => {
    if (!checkArchitecture()) return
    try {
      await saveGenerationTargets()
      openGenerationStream(
        "blueprint",
        "生成章节目录",
        `/api/v1/projects/${id}/generate/blueprint`,
        "generation",
        "Novel_directory.txt",
      )
    } catch (error: any) {
      toast.error(error?.message || "目录生成启动失败")
    }
  }

  const handleUploadKnowledge = async () => {
    if (!knowledgeFile) return
    setKnowledgeLoading(true)
    try {
      const result = await api.knowledge.upload(id, knowledgeFile)
      toast.success(result.message || "上传成功")
      setKnowledgeFile(null)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "知识库上传失败")
    } finally {
      setKnowledgeLoading(false)
    }
  }

  const handleClearVector = async () => {
    try {
      await api.knowledge.clearVector(id)
      toast.success("向量库已清空")
      setClearDialogOpen(false)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "清空向量库失败")
    }
  }

  const handleStopGeneration = async () => {
    if (!generationTaskId) return
    setGenerationStopping(true)
    try {
      const result = await api.generate.cancelTask(id, generationTaskId)
      toast.info(result.message || "已请求中断")
    } catch (error: any) {
      setGenerationStopping(false)
      toast.error(error?.message || "中断请求失败")
    }
  }

  const handleDeleteKnowledgeFile = async (file: any) => {
    try {
      await api.knowledge.delete(id, file.id)
      toast.success(`已删除 ${file.filename}`)
      setKnowledgeDeleteTarget(null)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "删除知识库文件失败")
    }
  }

  const handleReimportKnowledgeFile = async (file: any) => {
    try {
      const result = await api.knowledge.reimport(id, file.id)
      toast.success(result.message || `已重新导入 ${file.filename}`)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "重新导入失败")
    }
  }

  const completedChapters = chapters?.filter((chapter: any) => chapter.status === "final").length || 0
  const draftChapters = chapters?.filter((chapter: any) => chapter.status === "draft").length || 0
  const pendingChapters = chapters?.filter((chapter: any) => chapter.status !== "final" && chapter.status !== "draft").length || 0
  const totalWords = chapters?.reduce((sum: number, chapter: any) => sum + (chapter.word_count || 0), 0) || 0
  const selectedChapterFromList = chapters?.find((chapter: any) => chapter.chapter_number === selectedChapterNumber)
  const activeChapterMeta = chapterEditorMeta || selectedChapterFromList
  const appearedCharacters = characters.filter((char: any) => (char.status || "appeared") === "appeared")
  const plannedCharacters = characters.filter((char: any) => char.status === "planned")
  const suggestedCharacters = characters.filter((char: any) => char.status === "suggested")
  const readerScore = typeof hookResult?.score === "number" ? hookResult.score : null
  const readerRiskLabel = readerScore === null ? "待评估" : readerScore >= 8 ? "低流失" : readerScore >= 6 ? "中等风险" : "高流失风险"
  const readerRiskVariant: "default" | "outline" | "destructive" = readerScore === null ? "outline" : readerScore >= 7 ? "default" : "destructive"

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
        <Skeleton className="h-10 w-full max-w-md" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (!project) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="text-muted-foreground">{project.description || "暂无简介"}</p>
        </div>
        <Badge variant={project.status === "ready" ? "default" : "secondary"} className="text-sm px-3 py-1">
          {project.status === "draft" ? "草稿" : project.status === "ready" ? "就绪" : project.status}
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6 flex-wrap">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="workbench">章节工作台</TabsTrigger>
          <TabsTrigger value="generation">AI 生成</TabsTrigger>
          <TabsTrigger value="files">文件输出</TabsTrigger>
          <TabsTrigger value="knowledge">知识库</TabsTrigger>
          <TabsTrigger value="characters">人物规划</TabsTrigger>
          <TabsTrigger value="reader">读者反馈</TabsTrigger>
          <TabsTrigger value="platform">{PLATFORM_CONFIG[config?.platform]?.icon || "📖"} {PLATFORM_CONFIG[config?.platform]?.label || "平台"}工具</TabsTrigger>
          <TabsTrigger value="settings">参数设置</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">总章节</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{config?.num_chapters || 0}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">已完成</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{completedChapters}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">草稿章节</CardTitle></CardHeader>
              <CardContent><span className="text-3xl font-bold">{draftChapters}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">目标平台</CardTitle></CardHeader>
              <CardContent>
                <span className="text-xl font-semibold">
                  {config?.platform ? <>{PLATFORM_CONFIG[config.platform]?.icon} {PLATFORM_CONFIG[config.platform]?.label}</> : "-"}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">分类</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.category || "-"}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">风格/流派</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.genre || "-"}</span></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">每章字数</CardTitle></CardHeader>
              <CardContent><span className="text-xl font-semibold">{config?.word_number || "-"}</span></CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>快速操作</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button onClick={handleGenerateArchitecture} disabled={isConnected || Boolean(generationTaskId) || generationStopping}>
                <Play className="h-4 w-4 mr-2" />生成架构
              </Button>
              <Button onClick={handleGenerateBlueprint} disabled={isConnected || Boolean(generationTaskId) || generationStopping} variant="outline">
                <FileText className="h-4 w-4 mr-2" />生成章节目录
              </Button>
              <Separator orientation="vertical" className="h-8" />
              <Button variant="outline" onClick={() => api.export.download(id, "txt")}>
                <FileDown className="h-4 w-4 mr-2" />导出 TXT
              </Button>
              <Button variant="outline" onClick={() => api.export.download(id, "html")}>
                <FileDown className="h-4 w-4 mr-2" />导出 HTML
              </Button>
            <Button variant="outline" onClick={() => setActiveTab("files")}>
              <FileText className="h-4 w-4 mr-2" />查看生成文件
            </Button>
              <Button variant="outline" onClick={() => setActiveTab("workbench")}>
                <BookOpen className="h-4 w-4 mr-2" />进入章节工作台
              </Button>
            </CardContent>
          </Card>

          {/* ── 架构与目录状态卡片 ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ArchitectureStatusCard
              architecture={architectureFile}
              isLoading={archOutlineLoading}
              onImport={() => { setImportDialogFileType("architecture"); setImportDialogOpen(true) }}
              onRegenerate={handleGenerateArchitecture}
              onPreview={() => { setSelectedOutputFile("Novel_architecture.txt"); setActiveTab("files") }}
            />
            <OutlineStatusCard
              outline={outlineFile}
              hasArchitecture={!!architectureFile}
              isLoading={archOutlineLoading}
              onImport={() => { setImportDialogFileType("outline"); setImportDialogOpen(true) }}
              onRegenerate={handleGenerateBlueprint}
              onPreview={() => { setSelectedOutputFile("Novel_directory.txt"); setActiveTab("files") }}
            />
          </div>

          <Card>
            <CardHeader><CardTitle>章节列表</CardTitle></CardHeader>
            <CardContent>
              {!chapters?.length ? (
                <p className="text-muted-foreground text-sm">尚未生成章节目录，请先执行「生成架构」→「生成章节目录」</p>
              ) : (
                <ScrollArea className="h-64">
                  <div className="space-y-2">
                    {chapters.map((ch: any) => (
                      <div
                        key={ch.chapter_number}
                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer"
                        onClick={() => router.push(`/projects/${id}/chapter/${ch.chapter_number}`)}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="font-mono text-sm text-muted-foreground shrink-0">第{ch.chapter_number}章</span>
                          <span className="font-medium truncate">{ch.chapter_title || "未命名"}</span>
                          {ch.chapter_summary && (
                            <span className="text-sm text-muted-foreground truncate hidden md:block max-w-xs">{ch.chapter_summary}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-2">
                          {ch.word_count > 0 && <span className="text-xs text-muted-foreground hidden sm:inline">{ch.word_count}字</span>}
                          <Badge variant={ch.status === "final" ? "default" : "secondary"}>
                            {ch.status === "final" ? "已定稿" : ch.status === "draft" ? "草稿" : "待生成"}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="workbench" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Gauge className="h-5 w-5" />生成控制</CardTitle>
              <CardDescription>控制架构、目录和章节草稿的生成规模</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[150px_150px_150px_150px_minmax(0,1fr)]">
                <div>
                  <Label>总章节</Label>
                  <Input
                    type="number"
                    min={1}
                    value={generationChapterCount}
                    onChange={(event) => setGenerationChapterCount(Math.max(1, Number(event.target.value) || 1))}
                  />
                </div>
                <div>
                  <Label>每章字数</Label>
                  <Input
                    type="number"
                    min={500}
                    step={500}
                    value={generationWordCount}
                    onChange={(event) => setGenerationWordCount(Math.max(500, Number(event.target.value) || 500))}
                  />
                </div>
                <div>
                  <Label>当前章节</Label>
                  <Input
                    type="number"
                    min={1}
                    max={generationChapterCount || undefined}
                    value={selectedChapterNumber}
                    onChange={(event) => {
                      const value = Math.max(1, Number(event.target.value) || 1)
                      setSelectedChapterNumber(value)
                      setReaderChapterNum(value)
                      setHookChapterNum(value)
                    }}
                  />
                </div>
                <div>
                  <Label>本轮章数</Label>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    value={batchChapterCount}
                    onChange={(event) => setBatchChapterCount(Math.min(20, Math.max(1, Number(event.target.value) || 1)))}
                  />
                </div>
                <div className="flex flex-wrap items-end gap-2">
                  <Button variant="outline" onClick={handleApplyGenerationTargets} disabled={updateConfig.isPending}>
                    {updateConfig.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    保存控制
                  </Button>
                  <Button onClick={handleGenerateArchitecture} disabled={isConnected || Boolean(generationTaskId) || generationStopping}>
                    <Wand2 className="h-4 w-4 mr-2" />生成架构
                  </Button>
                  <Button onClick={handleGenerateBlueprint} disabled={isConnected || Boolean(generationTaskId) || generationStopping} variant="outline">
                    <ListChecks className="h-4 w-4 mr-2" />生成目录
                  </Button>
                  <Button onClick={handleGenerateWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping} variant="outline">
                    <Play className="h-4 w-4 mr-2" />生成本章
                  </Button>
                  <Button onClick={handleGenerateChapterBatch} disabled={isConnected || Boolean(generationTaskId) || generationStopping} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />批量生成
                  </Button>
                  {generationTaskId && (
                    <Button variant="destructive" onClick={handleStopGeneration} disabled={generationStopping || !isConnected}>
                      {generationStopping ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Ban className="h-4 w-4 mr-2" />}
                      中断生成
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">章节目录</CardTitle>
                <CardDescription>{completedChapters} 定稿 / {draftChapters} 草稿 / {pendingChapters} 待生成</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {!chapters?.length ? (
                  <div className="px-4 pb-4 text-sm text-muted-foreground">尚未生成章节目录</div>
                ) : (
                  <ScrollArea className="h-[66vh]">
                    <div className="space-y-1 p-2">
                      {chapters.map((chapter: any) => (
                        <button
                          key={chapter.chapter_number}
                          type="button"
                          onClick={() => {
                            setSelectedChapterNumber(chapter.chapter_number)
                            setReaderChapterNum(chapter.chapter_number)
                            setHookChapterNum(chapter.chapter_number)
                          }}
                          className={`w-full rounded-lg px-3 py-2 text-left transition ${
                            selectedChapterNumber === chapter.chapter_number ? "bg-primary/10 text-primary" : "hover:bg-accent"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs">第{chapter.chapter_number}章</span>
                            <Badge variant={chapter.status === "final" ? "default" : chapter.status === "draft" ? "secondary" : "outline"}>
                              {chapter.status === "final" ? "定稿" : chapter.status === "draft" ? "草稿" : "待写"}
                            </Badge>
                          </div>
                          <p className="mt-1 truncate text-sm font-medium">{chapter.chapter_title || "未命名"}</p>
                          {chapter.word_count > 0 && <p className="mt-1 text-xs text-muted-foreground">{chapter.word_count} 字</p>}
                        </button>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <CardTitle className="truncate">
                      第{selectedChapterNumber}章 {activeChapterMeta?.chapter_title || selectedChapterFromList?.chapter_title || ""}
                    </CardTitle>
                    <CardDescription className="truncate">
                      {activeChapterMeta?.chapter_summary || selectedChapterFromList?.chapter_summary || "章节内容编辑区"}
                    </CardDescription>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant={activeChapterMeta?.status === "final" ? "default" : activeChapterMeta?.status === "draft" ? "secondary" : "outline"}>
                      {activeChapterMeta?.status === "final" ? "已定稿" : activeChapterMeta?.status === "draft" ? "草稿" : "待生成"}
                    </Badge>
                    <Badge variant="outline">{activeChapterMeta?.word_count || chapterEditorContent.length || 0} 字</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && isConnected && (
                  <div className="flex items-center gap-2 rounded-lg bg-primary/10 p-3 text-sm text-primary">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>AI 正在处理第{selectedChapterNumber}章...</span>
                  </div>
                )}
                {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && events.filter(e => e.type === "progress").slice(-3).map((event, index) => (
                  <div key={`${event.data.step}-${index}`} className="flex items-start gap-2 rounded-lg bg-muted/50 p-2 text-sm">
                    {event.data.status === "done" ? <CheckCircle className="mt-0.5 h-4 w-4 text-green-500" /> : <Loader2 className="mt-0.5 h-4 w-4 animate-spin text-primary" />}
                    <span>{event.data.message}</span>
                  </div>
                ))}
                {(sseAction === "chapter" || sseAction === "chapterBatch" || sseAction === "finalize") && lastError && (
                  <div className="flex items-start gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{lastError.data?.message || "生成失败"}</span>
                  </div>
                )}

                {chapterEditorLoading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-[54vh] w-full rounded-lg" />
                  </div>
                ) : (
                  <Textarea
                    value={chapterEditorContent}
                    onChange={(event) => setChapterEditorContent(event.target.value)}
                    className="min-h-[54vh] resize-none font-serif text-base leading-7"
                    placeholder="在这里生成、编辑、保存章节草稿..."
                  />
                )}

                <div className="flex flex-wrap gap-2">
                  <Button onClick={handleSaveWorkbenchChapter} disabled={chapterEditorSaving || chapterEditorLoading}>
                    {chapterEditorSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    保存草稿
                  </Button>
                  <Button variant="outline" onClick={handleGenerateWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping}>
                    <Play className="h-4 w-4 mr-2" />AI 生成本章
                  </Button>
                  <Button variant="secondary" onClick={handleFinalizeWorkbenchChapter} disabled={isConnected || Boolean(generationTaskId) || generationStopping || !chapterEditorContent.trim()}>
                    <CheckCircle className="h-4 w-4 mr-2" />定稿
                  </Button>
                  {generationTaskId && (
                    <Button variant="destructive" onClick={handleStopGeneration} disabled={generationStopping || !isConnected}>
                      {generationStopping ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Ban className="h-4 w-4 mr-2" />}
                      中断生成
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">章节信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div><span className="text-muted-foreground">定位：</span>{activeChapterMeta?.chapter_role || "-"}</div>
                  <div><span className="text-muted-foreground">核心作用：</span>{activeChapterMeta?.chapter_purpose || "-"}</div>
                  <div><span className="text-muted-foreground">悬念密度：</span>{activeChapterMeta?.suspense_level || "-"}</div>
                  <div><span className="text-muted-foreground">伏笔操作：</span>{activeChapterMeta?.foreshadowing || "-"}</div>
                  <div><span className="text-muted-foreground">认知颠覆：</span>{activeChapterMeta?.plot_twist_level || "-"}</div>
                  <Separator />
                  <div><span className="text-muted-foreground">项目字数：</span>{totalWords} 字</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">平台编辑</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button className="w-full justify-start" variant="outline" onClick={handleWorkbenchOpeningHook} disabled={platformLoading === "workbenchOpening"}>
                    {platformLoading === "workbenchOpening" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Target className="h-4 w-4 mr-2" />}
                    检测开篇钩子
                  </Button>
                  <Button className="w-full justify-start" variant="outline" onClick={handleWorkbenchEndingHook} disabled={platformLoading === "workbenchEnding"}>
                    {platformLoading === "workbenchEnding" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Eye className="h-4 w-4 mr-2" />}
                    检测结尾钩子
                  </Button>
                  <Button className="w-full justify-start" variant="outline" onClick={handleGenSelectedChapterTitle} disabled={platformLoading === "workbenchTitle"}>
                    {platformLoading === "workbenchTitle" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileEdit className="h-4 w-4 mr-2" />}
                    生成章节标题
                  </Button>

                  {chapterTitles.length > 0 && (
                    <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs text-muted-foreground">标题候选</p>
                      {chapterTitles.map((title, index) => <p key={index} className="text-sm">「{title}」</p>)}
                    </div>
                  )}
                  {hookResult && (
                    <div className="space-y-2 rounded-lg border p-3 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">开篇评分</span>
                        <Badge variant={hookResult.score >= 7 ? "default" : "destructive"}>{hookResult.score}/10</Badge>
                      </div>
                      {hookResult.rewrite_suggestion && <p className="text-muted-foreground">{hookResult.rewrite_suggestion}</p>}
                    </div>
                  )}
                  {chapterHookResult && (
                    <div className="space-y-2 rounded-lg border p-3 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">结尾钩子</span>
                        <Badge variant={chapterHookResult.has_hook ? "default" : "destructive"}>
                          {chapterHookResult.has_hook ? "有钩子" : "需加强"}
                        </Badge>
                      </div>
                      {chapterHookResult.suggestion && <p className="text-muted-foreground">{chapterHookResult.suggestion}</p>}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="generation">
          <Card>
            <CardHeader>
              <CardTitle>AI 生成进度</CardTitle>
              <CardDescription>实时显示生成状态</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(generationTaskId || generationTaskLabel) && (
                <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium truncate">{generationTaskLabel || "当前生成任务"}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        任务 ID: {generationTaskId || "待分配"}
                      </p>
                    </div>
                    <Badge variant={generationStopping ? "secondary" : "outline"}>
                      {generationStopping ? "停止中" : isConnected ? "进行中" : "待完成"}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="destructive" onClick={handleStopGeneration} disabled={!generationTaskId || generationStopping || !isConnected}>
                      {generationStopping ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Ban className="h-4 w-4 mr-2" />}
                      中断生成
                    </Button>
                  </div>
                </div>
              )}

              {events.length === 0 && !isConnected && (
                <div className="text-center py-8 text-muted-foreground">
                  <Play className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>点击上方的「生成架构」或「生成章节目录」开始</p>
                </div>
              )}

              {isConnected && (
                <div className="flex items-center gap-2 text-primary">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>AI 正在生成中...</span>
                </div>
              )}

              {events.filter(e => e.type === "progress").map((e, i) => {
                const meta = generationStepMeta(e.data?.step)
                return (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                    {e.data.status === "done" ? (
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
                    ) : (
                      <Loader2 className="h-5 w-5 animate-spin text-primary mt-0.5 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{e.data.message}</p>
                        <Badge variant="outline">{meta.label}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{meta.description}</p>
                      <p className="text-xs text-muted-foreground">内部步骤: {e.data.step}</p>
                    </div>
                  </div>
                )
              })}

              {hasError && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-destructive/10 text-destructive">
                  <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
                  <p className="font-medium">{lastError?.data?.message || "生成过程中出现错误"}</p>
                </div>
              )}

              {lastPartial && (
                <div className="p-4 rounded-lg border bg-muted/30">
                  <p className="text-xs text-muted-foreground mb-2">生成预览：</p>
                  <pre className="text-sm whitespace-pre-wrap font-sans">{lastPartial.data.content}</pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="files" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>生成文件</CardTitle>
                  <CardDescription>这里集中查看架构、章节目录、摘要、角色状态等生成产物</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => loadOutputFile(selectedOutputFile)} disabled={outputFileLoading}>
                    {outputFileLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    刷新
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleCopyOutput} disabled={!outputFileContent}>
                    <Copy className="h-4 w-4 mr-2" />
                    复制
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownloadOutput} disabled={outputFileLoading}>
                    <FileDown className="h-4 w-4 mr-2" />
                    下载
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => setDeleteOutputDialogOpen(true)} disabled={outputFileLoading}>
                    <Trash2 className="h-4 w-4 mr-2" />
                    删除
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                <div className="space-y-2">
                  {GENERATED_FILES.map((file) => (
                    <button
                      key={file.filename}
                      type="button"
                      onClick={() => setSelectedOutputFile(file.filename)}
                      className={`w-full rounded-lg border p-3 text-left transition ${
                        selectedOutputFile === file.filename ? "border-primary bg-primary/5" : "hover:bg-accent"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 shrink-0" />
                        <span className="font-medium">{file.label}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{file.description}</p>
                    </button>
                  ))}
                </div>

                <div className="rounded-lg border bg-muted/20">
                  <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
                    <div className="min-w-0">
                      <p className="font-medium">{GENERATED_FILES.find((file) => file.filename === selectedOutputFile)?.label}</p>
                      <p className="text-xs text-muted-foreground">{selectedOutputFile}</p>
                    </div>
                    <Badge variant="outline">
                      {outputFileLoading ? "加载中" : outputFileError ? "异常" : outputFileContent ? "已读取" : "待读取"}
                    </Badge>
                  </div>
                  <ScrollArea className="h-[60vh]">
                    <div className="p-4">
                      {outputFileLoading ? (
                        <div className="space-y-3">
                          <Skeleton className="h-4 w-3/4" />
                          <Skeleton className="h-4 w-1/2" />
                          <Skeleton className="h-4 w-5/6" />
                          <Skeleton className="h-4 w-2/3" />
                        </div>
                      ) : outputFileError ? (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                          {outputFileError}
                        </div>
                      ) : outputFileContent ? (
                        <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-6">{outputFileContent}</pre>
                      ) : (
                        <p className="text-sm text-muted-foreground">点击左侧文件查看内容。</p>
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                架构生成后会写入 <code>Novel_architecture.txt</code>、<code>global_summary.txt</code> 和 <code>plot_arcs.txt</code>，章节目录、角色状态也会分别保存在对应文件中。
              </p>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="knowledge" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>知识库管理</CardTitle>
              <CardDescription>上传 TXT 设定文档，AI 会在生成章节时自动检索相关内容。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <Input type="file" accept=".txt,.md" onChange={e => setKnowledgeFile(e.target.files?.[0] || null)} className="flex-1" />
                <Button onClick={handleUploadKnowledge} disabled={!knowledgeFile || knowledgeLoading}>
                  {knowledgeLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                  上传并导入
                </Button>
              </div>
              <Separator />
              <Button variant="destructive" onClick={() => setClearDialogOpen(true)} disabled={knowledgeLoading}>
                <Trash2 className="h-4 w-4 mr-2" />清空向量库
              </Button>
              {knowledgeError && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                  {knowledgeError}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-base">知识库文件列表</CardTitle>
                  <CardDescription>可查看、重导入或删除单个知识文件</CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={() => void refreshKnowledgeFiles()} disabled={knowledgeLoading}>
                  {knowledgeLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                  刷新
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {knowledgeLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : knowledgeFiles.length === 0 ? (
                <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  暂无知识库文件
                </div>
              ) : (
                <div className="space-y-3">
                  {knowledgeFiles.map((file: any) => (
                    <div key={file.id} className="rounded-lg border p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-medium truncate">{file.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(file.file_size)} · {file.imported ? "已导入向量库" : "未导入"}
                            {file.created_at ? ` · ${file.created_at.slice(0, 19).replace("T", " ")}` : ""}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant={file.imported ? "default" : "outline"}>{file.imported ? "已导入" : "待导入"}</Badge>
                          <Button variant="outline" size="sm" onClick={() => handleReimportKnowledgeFile(file)} disabled={knowledgeLoading}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            重导入
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => setKnowledgeDeleteTarget(file)} disabled={knowledgeLoading}>
                            <Trash2 className="h-4 w-4 mr-2" />
                            删除
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="characters" className="space-y-6">
          <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2"><Users className="h-5 w-5" />人物规划</CardTitle>
                  <CardDescription>角色资料 · 关系图 · 冲突网 · 登场时间线</CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={handleImportCharacters} disabled={characterImportLoading}>
                    {characterImportLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                    预览导入
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleSuggestCharacters} disabled={characterLoading === "suggest"}>
                    {characterLoading === "suggest" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                    AI 生成人物
                  </Button>
                  <Button size="sm" onClick={() => openCreateDialog("planned", "user")}>
                    <UserPlus className="h-4 w-4 mr-2" />新增计划人物
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* 角色库概览 */}
          {dashboardSummary && (
            <div className="grid grid-cols-5 gap-3">
              {[
                { label: "人物", value: dashboardSummary.total_characters, sub: `${dashboardSummary.appeared}登场·${dashboardSummary.planned}计划·${dashboardSummary.suggested}建议` },
                { label: "关系", value: dashboardSummary.total_relationships, sub: `${dashboardSummary.active_relationships} 活跃` },
                { label: "冲突", value: dashboardSummary.total_conflicts, sub: `${dashboardSummary.active_conflicts} 进行中` },
                { label: "登场", value: dashboardSummary.total_appearances, sub: `${dashboardSummary.chapters_with_data} 章有数据` },
              ].map(s => (
                <Card key={s.label} className="bg-muted/30"><CardContent className="p-3 text-center">
                  <p className="text-2xl font-bold">{s.value}</p>
                  <p className="text-xs font-medium text-muted-foreground">{s.label}</p>
                  {s.sub && <p className="text-xs text-muted-foreground mt-0.5">{s.sub}</p>}
                </CardContent></Card>
              ))}
            </div>
          )}

          {/* 角色管理子标签 */}
          <Tabs defaultValue="roster">
            <TabsList className="mb-4 flex-wrap">
              <TabsTrigger value="roster"><Users className="h-4 w-4 mr-1" />人物列表</TabsTrigger>
              <TabsTrigger value="relationships"><GitBranch className="h-4 w-4 mr-1" />关系图</TabsTrigger>
              <TabsTrigger value="conflicts"><Swords className="h-4 w-4 mr-1" />冲突网</TabsTrigger>
              <TabsTrigger value="timeline"><Clock className="h-4 w-4 mr-1" />登场时间线</TabsTrigger>
            </TabsList>

            <TabsContent value="roster">
              {characterSuggestions.length > 0 && (
                <Card className="mb-4">
                  <CardHeader>
                    <CardTitle className="text-base">本次 AI 建议</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {characterSuggestions.map((suggestion: any) => (
                      <div key={suggestion.name} className="rounded-lg border p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{suggestion.name}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{suggestion.description}</p>
                          </div>
                          <Badge variant="outline">AI 建议</Badge>
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-2">
                          <span className="text-xs text-muted-foreground">
                            {suggestion.first_appearance_chapter ? `预计第${suggestion.first_appearance_chapter}章` : "登场待定"}
                          </span>
                          <Button size="sm" variant="outline" onClick={() => handleAcceptCharacterSuggestion(suggestion)}>
                            <PlusCircle className="h-4 w-4 mr-2" />加入计划
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              <div className="grid gap-6 lg:grid-cols-3">
                {[
                  { title: "已出现人物", items: appearedCharacters, empty: "从角色状态导入后会出现在这里" },
                  { title: "计划登场人物", items: plannedCharacters, empty: "你准备安排的人物会出现在这里" },
                  { title: "AI 建议人物", items: suggestedCharacters, empty: "AI 生成但尚未采纳的人物会出现在这里" },
                ].map((group) => (
                  <Card key={group.title}>
                    <CardHeader>
                      <CardTitle className="text-base">{group.title}</CardTitle>
                      <CardDescription>{group.items.length} 个</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {group.items.length === 0 ? (
                        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">{group.empty}</div>
                      ) : (
                        <div className="space-y-3">
                          {group.items.map((char: any) => (
                            <div key={char.id} className="rounded-lg border p-3 hover:bg-accent">
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0 flex-1 cursor-pointer" onClick={() => openEditDialog(char)}>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <p className="font-medium">{char.name}</p>
                                    <Badge variant="outline">{characterSourceLabel(char.source)}</Badge>
                                  </div>
                                  {char.description && <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">{char.description}</p>}
                                  <p className="mt-2 text-xs text-muted-foreground">
                                    {characterStatusLabel(char.status)}
                                    {char.first_appearance_chapter ? ` · 第${char.first_appearance_chapter}章登场` : ""}
                                  </p>
                                </div>
                                <Button variant="ghost" size="icon" onClick={() => setDeleteCharTarget(char.id)}>
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="relationships">
              <RelationshipManager projectId={id} characters={characters} />
            </TabsContent>

            <TabsContent value="conflicts">
              <ConflictManager projectId={id} characters={characters} />
            </TabsContent>

            <TabsContent value="timeline">
              <AppearanceTimeline projectId={id} characters={characters} />
            </TabsContent>
          </Tabs>
        </div>
        </TabsContent>

        <TabsContent value="reader" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2"><MessageSquare className="h-5 w-5" />读者反馈</CardTitle>
                  <CardDescription>把开篇吸引力、结尾钩子和章节标题放到同一处看</CardDescription>
                </div>
                <div className="flex flex-wrap items-end gap-2">
                  <div>
                    <Label>章节</Label>
                    <Input
                      type="number"
                      min={1}
                      className="w-24"
                      value={readerChapterNum}
                      onChange={(event) => setReaderChapterNum(Math.max(1, Number(event.target.value) || 1))}
                    />
                  </div>
                  <Button variant="outline" onClick={handleReaderOpeningCheck} disabled={platformLoading === "readerOpening"}>
                    {platformLoading === "readerOpening" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Target className="h-4 w-4 mr-2" />}
                    开篇反馈
                  </Button>
                  <Button variant="outline" onClick={handleReaderEndingCheck} disabled={platformLoading === "readerEnding"}>
                    {platformLoading === "readerEnding" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Eye className="h-4 w-4 mr-2" />}
                    结尾反馈
                  </Button>
                  <Button variant="outline" onClick={handleBatchHookCheck} disabled={platformLoading === "batch"}>
                    {platformLoading === "batch" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    全书结尾钩子
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">首屏吸引力</CardTitle>
                <CardDescription>第{readerChapterNum}章</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">流失风险</span>
                  <Badge variant={readerRiskVariant}>{readerRiskLabel}</Badge>
                </div>
                <div className="text-4xl font-bold">{readerScore ?? "-"}<span className="text-base font-normal text-muted-foreground">/10</span></div>
                {hookResult?.hook_strength && <Badge variant="outline">{hookResult.hook_strength}</Badge>}
                {hookResult?.issues?.length > 0 && (
                  <div className="space-y-1 text-sm text-muted-foreground">
                    {hookResult.issues.map((issue: string, index: number) => <p key={index}>- {issue}</p>)}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">结尾追读</CardTitle>
                <CardDescription>第{readerChapterNum}章</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">钩子状态</span>
                  <Badge variant={chapterHookResult?.has_hook ? "default" : "outline"}>
                    {chapterHookResult ? (chapterHookResult.has_hook ? "有钩子" : "需加强") : "待检测"}
                  </Badge>
                </div>
                {chapterHookResult?.hook_type && <Badge variant="secondary">{chapterHookResult.hook_type}</Badge>}
                {chapterHookResult?.hook_description && <p className="text-sm">{chapterHookResult.hook_description}</p>}
                {chapterHookResult?.suggestion && <p className="text-sm text-muted-foreground">{chapterHookResult.suggestion}</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">平台信号</CardTitle>
                <CardDescription>{PLATFORM_CONFIG[config?.platform]?.label || "平台"}视角</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">章节完成</span>
                  <span>{completedChapters}/{config?.num_chapters || chapters?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">草稿库存</span>
                  <span>{draftChapters}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">累计字数</span>
                  <span>{totalWords}</span>
                </div>
                {tagsResult?.target_audience && (
                  <div className="rounded-lg border bg-muted/30 p-3 text-muted-foreground">{tagsResult.target_audience}</div>
                )}
              </CardContent>
            </Card>
          </div>

          {hookResult?.rewrite_suggestion && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">改写建议</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm">{hookResult.rewrite_suggestion}</p>
                {hookResult.rewritten_opening && (
                  <div className="rounded-lg border bg-muted/30 p-4 text-sm leading-7">{hookResult.rewritten_opening}</div>
                )}
              </CardContent>
            </Card>
          )}

          {batchHookResult.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">全书结尾钩子</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {batchHookResult.map((result: any) => (
                    <div key={result.chapter_number} className="rounded-lg border p-3 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono">第{result.chapter_number}章</span>
                        <Badge variant={result.has_hook ? "default" : "destructive"}>{result.has_hook ? "有钩子" : "缺钩子"}</Badge>
                      </div>
                      {result.hook_type && <p className="mt-2 text-muted-foreground">{result.hook_type}</p>}
                      {result.suggestion && <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{result.suggestion}</p>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* 番茄平台工具 Tab */}
        <TabsContent value="platform">
          <div className="grid gap-6">
            {/* 1. 书名生成 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><BookMarked className="h-5 w-5" />AI 书名生成</CardTitle>
                <CardDescription>根据小说设定，用平台爆款公式（身份反转+冲突 / 悬念+关键词 / 情绪+结果前置）生成书名候选</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={handleGenTitles} disabled={platformLoading === "titles"}>
                  {platformLoading === "titles" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                  生成书名
                </Button>
                {titles.length > 0 && (
                  <div className="space-y-2">
                    {titles.map((t, i) => (
                      <div key={i} className="p-3 rounded-lg border bg-muted/30 text-sm flex items-start gap-2">
                        <Badge variant="outline" className="shrink-0 mt-0.5">{i + 1}</Badge>
                        <span>{t}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 2. 简介生成 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><FileEdit className="h-5 w-5" />AI 简介生成</CardTitle>
                <CardDescription>用「核心冲突 + 金手指 + 爽点预告 + 悬念钩子」公式生成平台式简介</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={handleGenBlurb} disabled={platformLoading === "blurb"}>
                  {platformLoading === "blurb" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                  生成简介
                </Button>
                {blurbs.map((b, i) => (
                  <div key={i} className="p-4 rounded-lg border bg-muted/30">
                    <p className="text-xs text-muted-foreground mb-1">版本 {i + 1}</p>
                    <p className="text-sm leading-relaxed">{b}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* 3. 钩子检测 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Target className="h-5 w-5" />开篇 & 章节钩子检测</CardTitle>
                <CardDescription>检查前200字是否有强冲突/悬念，以及每章结尾是否留了钩子。平台算法核心指标。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm">章节号：</span>
                  <Input type="number" value={hookChapterNum} onChange={e => setHookChapterNum(+e.target.value)} className="w-20" min={1} />
                  <Button onClick={handleHookCheck} disabled={platformLoading === "hook"} variant="outline">
                    {platformLoading === "hook" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Target className="h-4 w-4 mr-2" />}
                    检测开篇钩子
                  </Button>
                  <Button onClick={handleGenChapterTitle} disabled={platformLoading === "chapterTitle"} variant="outline">
                    {platformLoading === "chapterTitle" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileEdit className="h-4 w-4 mr-2" />}
                    生成章节标题
                  </Button>
                  <Separator orientation="vertical" className="h-8" />
                  <Button onClick={handleBatchHookCheck} disabled={platformLoading === "batch"} variant="outline">
                    {platformLoading === "batch" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    批量检测所有章节结尾钩子
                  </Button>
                </div>

                {hookResult && (
                  <div className="p-4 rounded-lg border space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">评分：</span>
                      <Badge variant={hookResult.score >= 7 ? "default" : "destructive"}>{hookResult.score}/10</Badge>
                      <Badge variant="outline">{hookResult.hook_strength}</Badge>
                    </div>
                    {hookResult.issues?.length > 0 && (
                      <div className="text-sm text-muted-foreground">
                        <span className="text-destructive font-medium">问题：</span>
                        {hookResult.issues.map((issue: string, i: number) => (
                          <p key={i} className="ml-2">- {issue}</p>
                        ))}
                      </div>
                    )}
                    {hookResult.rewrite_suggestion && <p className="text-sm">建议：{hookResult.rewrite_suggestion}</p>}
                    {hookResult.rewritten_opening && (
                      <div className="p-3 rounded bg-muted/50 text-sm">
                        <p className="text-xs text-muted-foreground mb-1">改写示例：</p>
                        <p>{hookResult.rewritten_opening}</p>
                      </div>
                    )}
                  </div>
                )}

                {chapterTitles.length > 0 && (
                  <div className="space-y-1 p-3 rounded-lg border bg-muted/30">
                    <p className="text-xs text-muted-foreground mb-2">章节标题候选：</p>
                    {chapterTitles.map((t, i) => <p key={i} className="text-sm">「{t}」</p>)}
                  </div>
                )}

                {batchHookResult.length > 0 && (
                  <div className="space-y-2 max-h-64 overflow-auto">
                    <p className="text-sm font-medium">批量检测结果：</p>
                    {batchHookResult.map((r: any) => (
                      <div key={r.chapter_number} className="flex items-center gap-3 p-2 rounded border text-sm">
                        <span className="font-mono">第{r.chapter_number}章</span>
                        <Badge variant={r.has_hook ? "default" : "destructive"}>{r.has_hook ? "有钩子" : "缺钩子"}</Badge>
                        {r.hook_type && <span className="text-muted-foreground">{r.hook_type}</span>}
                        {r.suggestion && <span className="text-muted-foreground text-xs truncate">{r.suggestion}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 4. 标签生成 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Tag className="h-5 w-5" />平台标签 & 关键词</CardTitle>
                <CardDescription>生成适配平台搜索算法的标签和关键词，提升搜索曝光</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={handleGenTags} disabled={platformLoading === "tags"}>
                  {platformLoading === "tags" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                  生成标签
                </Button>
                {tagsResult && (
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-medium mb-2">主标签：</p>
                      <div className="flex flex-wrap gap-2">
                        {tagsResult.main_tags?.map((t: string, i: number) => <Badge key={i} className="cursor-default">{t}</Badge>)}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium mb-2">搜索关键词：</p>
                      <div className="flex flex-wrap gap-2">
                        {tagsResult.search_keywords?.map((k: string, i: number) => <Badge key={i} variant="secondary" className="cursor-default">{k}</Badge>)}
                      </div>
                    </div>
                    {tagsResult.category_recommendation && <p className="text-sm">推荐分类：<span className="font-medium">{tagsResult.category_recommendation}</span></p>}
                    {tagsResult.target_audience && <p className="text-sm text-muted-foreground">目标读者：{tagsResult.target_audience}</p>}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader><CardTitle>项目参数</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label>目标平台</Label>
                  <Select value={config?.platform || "tomato"} onValueChange={(v) => updateConfig.mutate({ platform: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {PLATFORMS.map((key) => (
                        <SelectItem key={key} value={key}>
                          {PLATFORM_CONFIG[key].icon} {PLATFORM_CONFIG[key].label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>分类</Label>
                  <Input defaultValue={config?.category} onBlur={e => debouncedUpdate({ category: e.target.value })} />
                </div>
                <div>
                  <Label>风格/流派</Label>
                  <Input defaultValue={config?.genre} onBlur={e => debouncedUpdate({ genre: e.target.value })} />
                </div>
                <div>
                  <Label>主题</Label>
                  <Input defaultValue={config?.topic} onBlur={e => debouncedUpdate({ topic: e.target.value })} />
                </div>
                <div>
                  <Label>章节数</Label>
                  <Input type="number" defaultValue={config?.num_chapters} onBlur={e => debouncedUpdate({ num_chapters: +e.target.value })} />
                </div>
                <div>
                  <Label>每章字数</Label>
                  <Input type="number" defaultValue={config?.word_number} onBlur={e => debouncedUpdate({ word_number: +e.target.value })} />
                </div>
              </div>
              <div>
                <Label>内容指导（大纲）</Label>
                <Textarea
                  defaultValue={config?.user_guidance}
                  rows={8}
                  onBlur={e => debouncedUpdate({ user_guidance: e.target.value })}
                  placeholder="在这里描述你的大纲、世界观、角色构想..."
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>模型分配</CardTitle><CardDescription>为每个生成阶段选择使用的 LLM 模型和 Embedding 服务。留空则使用默认配置。</CardDescription></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label>架构生成</Label>
                  <Select value={config?.architecture_llm || ""} onValueChange={(v) => updateConfig.mutate({ architecture_llm: v || undefined } as any)}>
                    <SelectTrigger><SelectValue placeholder="默认（第一个可用）" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">默认（第一个可用）</SelectItem>
                      {Object.keys(llmConfigs).sort().map(name => <SelectItem key={name} value={name}>{name} [{usageLabel(llmConfigs[name]?.usage)}] - {llmConfigs[name]?.model_name || ""}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>章节目录</Label>
                  <Select value={config?.chapter_outline_llm || ""} onValueChange={(v) => updateConfig.mutate({ chapter_outline_llm: v || undefined } as any)}>
                    <SelectTrigger><SelectValue placeholder="默认（第一个可用）" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">默认（第一个可用）</SelectItem>
                      {Object.keys(llmConfigs).sort().map(name => <SelectItem key={name} value={name}>{name} [{usageLabel(llmConfigs[name]?.usage)}] - {llmConfigs[name]?.model_name || ""}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>章节草稿</Label>
                  <Select value={config?.prompt_draft_llm || ""} onValueChange={(v) => updateConfig.mutate({ prompt_draft_llm: v || undefined } as any)}>
                    <SelectTrigger><SelectValue placeholder="默认（第一个可用）" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">默认（第一个可用）</SelectItem>
                      {Object.keys(llmConfigs).sort().map(name => <SelectItem key={name} value={name}>{name} [{usageLabel(llmConfigs[name]?.usage)}] - {llmConfigs[name]?.model_name || ""}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>章节定稿</Label>
                  <Select value={config?.final_chapter_llm || ""} onValueChange={(v) => updateConfig.mutate({ final_chapter_llm: v || undefined } as any)}>
                    <SelectTrigger><SelectValue placeholder="默认（第一个可用）" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">默认（第一个可用）</SelectItem>
                      {Object.keys(llmConfigs).sort().map(name => <SelectItem key={name} value={name}>{name} [{usageLabel(llmConfigs[name]?.usage)}] - {llmConfigs[name]?.model_name || ""}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>一致性审校</Label>
                  <Select value={config?.consistency_review_llm || ""} onValueChange={(v) => updateConfig.mutate({ consistency_review_llm: v || undefined } as any)}>
                    <SelectTrigger><SelectValue placeholder="默认（第一个可用）" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">默认（第一个可用）</SelectItem>
                      {Object.keys(llmConfigs).sort().map(name => <SelectItem key={name} value={name}>{name} [{usageLabel(llmConfigs[name]?.usage)}] - {llmConfigs[name]?.model_name || ""}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Embedding 向量化</Label>
                  <Select value={config?.embedding_config || ""} onValueChange={(v) => updateConfig.mutate({ embedding_config: v || undefined } as any)}>
                    <SelectTrigger><SelectValue placeholder="不使用" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">不使用</SelectItem>
                      {Object.keys(embConfigs).sort().map(name => <SelectItem key={name} value={name}>{embConfigs[name]?.model_name || name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认清空向量库</DialogTitle>
            <DialogDescription>
              此操作将删除所有已导入的知识库向量数据，不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={handleClearVector}>确认清空</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!knowledgeDeleteTarget} onOpenChange={(open) => { if (!open) setKnowledgeDeleteTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除知识文件</DialogTitle>
            <DialogDescription>
              将删除 {knowledgeDeleteTarget?.filename || "该文件"}，并同步重建知识库向量。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setKnowledgeDeleteTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={() => knowledgeDeleteTarget && handleDeleteKnowledgeFile(knowledgeDeleteTarget)}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOutputDialogOpen} onOpenChange={setDeleteOutputDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除生成文件</DialogTitle>
            <DialogDescription>
              将删除 {GENERATED_FILES.find((file) => file.filename === selectedOutputFile)?.label || selectedOutputFile}。
              {selectedOutputFile === "Novel_directory.txt" ? " 章节目录删除后，章节规划列表也会同步清空，但已生成的章节正文文件会保留。" : " 此操作不会影响其他生成文件。"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOutputDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteOutputFile}>确认删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={charDialogOpen} onOpenChange={(v) => { if (!v) { setCharDialogOpen(false); setEditChar(null) } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editChar ? "编辑角色" : "新增角色"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>角色名称</Label>
              <Input value={charName} onChange={e => setCharName(e.target.value)} placeholder="例如：主角名字" />
            </div>
            <div>
              <Label>描述</Label>
              <Textarea value={charDesc} onChange={e => setCharDesc(e.target.value)} rows={4} placeholder="角色的外貌、性格、背景故事等" />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <Label>人物状态</Label>
                <Select value={charStatus} onValueChange={(value) => value && setCharStatus(value)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CHARACTER_STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>来源</Label>
                <Select value={charSource} onValueChange={(value) => value && setCharSource(value)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CHARACTER_SOURCE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>预计/首次登场章节</Label>
              <Input
                type="number"
                min={1}
                value={charFirstChapter}
                onChange={(event) => setCharFirstChapter(event.target.value ? Math.max(1, Number(event.target.value) || 1) : "")}
                placeholder="留空表示未决定"
              />
            </div>
            <Button className="w-full" onClick={editChar ? handleUpdateCharacter : handleCreateCharacter} disabled={!charName.trim()}>
              {editChar ? "保存修改" : "创建"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteCharTarget !== null} onOpenChange={(v) => { if (!v) setDeleteCharTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除角色</DialogTitle>
            <DialogDescription>此操作不可撤销。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteCharTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteCharacter}>确认删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={characterImportPreviewOpen} onOpenChange={(open) => { if (!open) setCharacterImportPreviewOpen(false) }}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>导入角色预览</DialogTitle>
            <DialogDescription>
              先筛选候选项，再确认写入角色库。推荐项已默认勾选，拒绝项不会自动导入。
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 sm:grid-cols-4">
            <Card className="border-dashed">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">总候选</p>
                <p className="mt-1 text-2xl font-semibold">{characterImportSummary?.total ?? characterImportCandidates.length}</p>
              </CardContent>
            </Card>
            <Card className="border-dashed">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">保留</p>
                <p className="mt-1 text-2xl font-semibold">{characterImportSummary?.keep ?? 0}</p>
              </CardContent>
            </Card>
            <Card className="border-dashed">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">复核</p>
                <p className="mt-1 text-2xl font-semibold">{characterImportSummary?.review ?? 0}</p>
              </CardContent>
            </Card>
            <Card className="border-dashed">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">已选中</p>
                <p className="mt-1 text-2xl font-semibold">{characterImportSelectedIds.length}</p>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => selectCharacterImportCandidates("recommended")}>选推荐项</Button>
            <Button variant="outline" size="sm" onClick={() => selectCharacterImportCandidates("all")}>全选</Button>
            <Button variant="ghost" size="sm" onClick={() => selectCharacterImportCandidates("none")}>清空</Button>
          </div>

          <ScrollArea className="h-[56vh] rounded-lg border">
            <div className="space-y-3 p-4">
              {characterImportCandidates.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                  没有可导入的角色候选项
                </div>
              ) : (
                characterImportCandidates.map((candidate: any) => {
                  const selected = characterImportSelectedIds.includes(candidate.candidate_id)
                  return (
                    <div
                      key={candidate.candidate_id}
                      className={`rounded-lg border p-3 transition ${selected ? "border-primary bg-primary/5" : ""}`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 shrink-0 rounded border-gray-300"
                          checked={selected}
                          onChange={() => toggleCharacterImportCandidate(candidate.candidate_id)}
                        />
                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium">{candidate.name}</p>
                            <Badge variant={candidate.decision === "keep" ? "default" : candidate.decision === "review" ? "outline" : "destructive"}>
                              {candidate.decision === "keep" ? "推荐导入" : candidate.decision === "review" ? "建议复核" : "建议排除"}
                            </Badge>
                            <Badge variant="outline">{candidate.entity_type || "character"}</Badge>
                            {candidate.existing_character_id && <Badge variant="secondary">已存在</Badge>}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            置信度 {Math.round((candidate.confidence || 0) * 100)}% · {candidate.section || "未识别分区"}
                            {candidate.first_appearance_chapter ? ` · 首次登场第 ${candidate.first_appearance_chapter} 章` : ""}
                          </p>
                          {candidate.description && <p className="text-sm text-muted-foreground">{candidate.description}</p>}
                          {candidate.reasons?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {candidate.reasons.slice(0, 4).map((reason: string, index: number) => (
                                <Badge key={index} variant="outline" className="text-xs">{reason}</Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </ScrollArea>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCharacterImportPreviewOpen(false)}>取消</Button>
            <Button onClick={handleConfirmCharacterImport} disabled={characterImportConfirming || characterImportSelectedIds.length === 0}>
              {characterImportConfirming ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              确认导入
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── 文件导入对话框 ── */}
      <FileImportDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        projectId={id}
        onImportSuccess={() => {
          loadArchitectureAndOutline()
          queryClient.invalidateQueries({ queryKey: ["chapters", id] })
        }}
      />
    </div>
  )
}
