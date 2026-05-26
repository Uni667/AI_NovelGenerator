"use client"

import { useState, useEffect } from "react"
import { useSSE } from "./use-sse"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export function useGenerationState(projectId: string) {
  const { events, isConnected, error: sseError, connect, disconnect: stopSse } = useSSE()
  const [generationTaskId, setGenerationTaskId] = useState<string | null>(null)
  const [generationStopping, setGenerationStopping] = useState(false)
  const [sseAction, setSseAction] = useState<string | null>(null)
  const [currentUrl, setCurrentUrl] = useState<string | null>(null)
  
  // Settings constraints
  const [generationChapterCount, setGenerationChapterCount] = useState(1)
  const [generationWordCount, setGenerationWordCount] = useState(2000)
  const [batchChapterCount, setBatchChapterCount] = useState(5)
  const [enableBrainstorming, setEnableBrainstorming] = useState(false)

  const generationTaskLabel = sseAction === "architecture" ? "架构与大纲" 
    : sseAction === "blueprint" ? "章节目录"
    : sseAction === "chapter" ? `生成章节草稿`
    : sseAction === "chapterBatch" ? `批量生成章节`
    : sseAction === "finalize" ? `定稿章节`
    : ""
    
  // Helper to map single chapter/blueprint/architecture steps to percentages
  const getStepPercentage = (action: string, step: string, status: string): number => {
    if (status === "done" && (step === "all" || step === "finalize" || step === "blueprint" || step === "draft")) {
      return 100
    }

    if (action === "architecture") {
      const mapping: Record<string, { running: number; done: number }> = {
        core_seed: { running: 5, done: 15 },
        character: { running: 20, done: 35 },
        character_state: { running: 40, done: 50 },
        world: { running: 55, done: 70 },
        plot: { running: 75, done: 85 },
        global_summary_init: { running: 90, done: 95 },
        plot_arcs_init: { running: 98, done: 100 },
        all: { running: 100, done: 100 }
      }
      const stepMap = mapping[step]
      if (stepMap) {
        return status === "done" ? stepMap.done : stepMap.running
      }
      return 0
    }
    
    if (action === "blueprint") {
      const mapping: Record<string, { running: number; done: number }> = {
        blueprint: { running: 10, done: 100 },
        blueprint_polish: { running: 50, done: 90 }
      }
      const stepMap = mapping[step]
      if (stepMap) {
        return status === "done" ? stepMap.done : stepMap.running
      }
      return 0
    }

    if (action === "finalize") {
      const mapping: Record<string, { running: number; done: number }> = {
        finalize: { running: 5, done: 100 },
        summary_update: { running: 10, done: 25 },
        character_state_update: { running: 30, done: 45 },
        plot_arcs_update: { running: 50, done: 65 },
        graph_extraction: { running: 70, done: 85 },
        single_summary_update: { running: 90, done: 95 }
      }
      const stepMap = mapping[step]
      if (stepMap) {
        return status === "done" ? stepMap.done : stepMap.running
      }
      return 0
    }

    return 0
  }

  const getSingleChapterProgress = (step: string, status: string): number => {
    const mapping: Record<string, { running: number; done: number }> = {
      build_prompt: { running: 5, done: 10 },
      brainstorm_reader: { running: 15, done: 20 },
      brainstorm_villain: { running: 22, done: 25 },
      brainstorm_director: { running: 28, done: 30 },
      draft: { running: 35, done: 100 },
      drafting: { running: 40, done: 65 },
      voice_polish: { running: 70, done: 80 },
      quality_check: { running: 85, done: 95 },
      quality_rewrite: { running: 88, done: 92 }
    }
    const stepMap = mapping[step]
    if (stepMap) {
      return status === "done" ? stepMap.done : stepMap.running
    }
    return 0
  }

  // Find the last progress event to calculate progress based on steps
  const progressEvents = events.filter((e) => e.type === "progress")
  const lastProgressEvent = progressEvents[progressEvents.length - 1]
  
  let rawProgress = 0
  if (lastProgressEvent && sseAction) {
    const step = lastProgressEvent.data?.step || ""
    const status = lastProgressEvent.data?.status || ""
    
    if (sseAction === "architecture") {
      if (step === "architecture_polish") {
        // Find the last progress event before this one that was NOT architecture_polish
        const lastNonPolish = [...progressEvents].reverse().find(e => e.data?.step && e.data.step !== "architecture_polish")
        const basePercent = lastNonPolish ? getStepPercentage("architecture", lastNonPolish.data.step, lastNonPolish.data.status) : 5
        rawProgress = basePercent + (status === "done" ? 8 : 4)
      } else {
        rawProgress = getStepPercentage("architecture", step, status)
      }
    } else if (sseAction === "blueprint") {
      rawProgress = getStepPercentage("blueprint", step, status)
    } else if (sseAction === "finalize") {
      rawProgress = getStepPercentage("finalize", step, status)
    } else if (sseAction === "chapterBatch") {
      const lastBatchEvent = [...progressEvents].reverse().find(e => e.data?.step === "batch")
      if (lastBatchEvent) {
        let currentChapterIndex = 1
        let totalChapters = 1
        if (lastBatchEvent.data?.message) {
          const match = lastBatchEvent.data.message.match(/（(\d+)\/(\d+)）/) || lastBatchEvent.data.message.match(/\((\d+)\/(\d+)\)/)
          if (match) {
            currentChapterIndex = parseInt(match[1], 10)
            totalChapters = parseInt(match[2], 10)
          }
        }
        
        const batchIdx = progressEvents.indexOf(lastBatchEvent)
        const subEvents = progressEvents.slice(batchIdx + 1)
        const lastSubEvent = subEvents[subEvents.length - 1]
        const subStep = lastSubEvent?.data?.step || ""
        const subStatus = lastSubEvent?.data?.status || ""
        
        const chapterProgress = getSingleChapterProgress(subStep, subStatus)
        rawProgress = Math.round(((currentChapterIndex - 1) / totalChapters) * 100 + (chapterProgress / totalChapters))
      } else {
        rawProgress = getSingleChapterProgress(step, status)
      }
    } else if (sseAction === "chapter") {
      rawProgress = getSingleChapterProgress(step, status)
    }
  }

  const lastEvent = events[events.length - 1]
  let generationProgress = rawProgress
  if (lastEvent?.type === "done") {
    generationProgress = 100
  } else if (!lastProgressEvent && isConnected) {
    generationProgress = 2
  }
  const generationRecovering = !isConnected && generationTaskId && !generationStopping
  const hasError = !!sseError

  const GENERATION_STEP_META: Record<string, { label: string; description: string }> = {
    core_seed: { label: "核心种子", description: "确定小说的核心卖点、主角欲望、主线冲突 and 读者情绪承诺" },
    character: { label: "角色架构", description: "设计角色总览、人物详卡、关系冲突网、出场路线和人设约束" },
    character_state: { label: "角色状态表", description: "把角色当前身份、目标、关系和秘密整理成后续章节可追踪的状态" },
    world: { label: "世界观", description: "确定故事规则、势力结构、资源体系和主角行动边界" },
    plot: { label: "三幕式情节架构", description: "把整本书拆成开局立钩子、中段冲突升级、后段爆发收束三段主线" },
    architecture_polish: { label: "架构优化", description: "压低上游工作文档的策划腔和会议纪要腔，减少对目录与正文的污染" },
    global_summary_init: { label: "初始全局摘要", description: "在架构完成后生成整本书的初始全局摘要，作为后续写作的连续性底稿" },
    plot_arcs_init: { label: "伏笔暗线台账", description: "在架构完成后建立伏笔、秘密、道具和反转的初始台账" },
    summary_update: { label: "全局摘要更新", description: "章节定稿后把新增事件、角色变化和已发生进展同步进摘要" },
    character_state_update: { label: "角色状态更新", description: "章节定稿后同步更新角色身份、关系、秘密和触发事件" },
    plot_arcs_update: { label: "伏笔暗线更新", description: "章节定稿后更新伏笔状态、回收计划和新增暗线" },
    all: { label: "架构汇总", description: "整合核心种子、人物、世界观和三幕式情节架构" },
    blueprint: { label: "章节目录", description: "把全书架构拆成章节标题、章节作用和每章推进目标" },
    blueprint_polish: { label: "目录优化", description: "压低章节蓝图的提纲腔和策划腔，减少对正文的反向污染" },
    build_prompt: { label: "章节提示词", description: "根据架构、目录和上下文构建当前章节写作提示" },
    draft: { label: "章节草稿", description: "生成当前章节正文草稿" },
    voice_polish: { label: "文风优化", description: "压低 AI 腔，收紧表达，保留剧情事实并增强现场感" },
    quality_check: { label: "平台质检", description: "按平台标准检查开篇抓力、信息密度和结尾钩子" },
    mid_check: { label: "中段质检", description: "检查正文中段是否发散、解释过多、剧情推进不足" },
    dialogue_check: { label: "对话质检", description: "检查人物台词是否同质化，是否都像作者在说话" },
    quality_rewrite: { label: "自动返修", description: "平台质检未达标时，自动强化开篇和结尾，并修正文风问题" },
    finalize: { label: "章节定稿", description: "定稿章节，并更新全局摘要、角色状态、伏笔暗线和后续上下文" },
    batch: { label: "批量章节生成", description: "按顺序生成多章草稿" },
    brainstorm_reader: { label: "读者脑暴", description: "毒舌读者 Agent 正在指出原大纲中套路化和缺乏张力的问题" },
    brainstorm_villain: { label: "反派密谋", description: "反派首脑 Agent 正在谋划突发危机或颠覆性反转" },
    brainstorm_director: { label: "导演统筹", description: "总导演 Agent 正在融合吐槽与计划，制定突发事件高燃指南" },
  }

  const generationStepMeta = (step?: string) => {
    if (!step) return { label: "生成步骤", description: "正在执行生成流程" }
    return GENERATION_STEP_META[step] || { label: step, description: "生成流程中的内部步骤" }
  }

  const handleStopGeneration = async () => {
    if (!generationTaskId) return
    setGenerationStopping(true)
    try {
      await api.generate.cancelTask(projectId, generationTaskId)
      toast.info("已发送终止请求")
      stopSse()
      setGenerationTaskId(null)
      setSseAction(null)
    } catch (error) {
      toast.error((error as Error).message || "终止失败")
    } finally {
      setGenerationStopping(false)
    }
  }

  const startTask = (actionName: string, url: string, taskId: string) => {
    setSseAction(actionName)
    setGenerationTaskId(taskId)
    
    // Ensure the URL has the task_id query parameter and absolute base URL
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    const urlObj = new URL(url, apiBase)
    urlObj.searchParams.set("task_id", taskId)
    const targetUrl = urlObj.toString()
    
    setCurrentUrl(targetUrl)
    connect(targetUrl)
  }

  const handleRetryGeneration = () => {
    if (!currentUrl || !generationTaskId || !sseAction) return
    
    // Find the last step we were working on
    let startStep = ""
    for (let i = events.length - 1; i >= 0; i--) {
      if (events[i].type === "progress" && events[i].data?.step) {
        startStep = events[i].data.step
        break
      }
    }
    
    if (startStep) {
      toast.info(`尝试从断点 "${generationStepMeta(startStep).label}" 恢复生成...`)
      const retryUrl = new URL(currentUrl)
      retryUrl.searchParams.set("start_step", startStep)
      connect(retryUrl.toString(), { preserveEvents: true })
    } else {
      // If no step found, just restart normally
      toast.info("重新开始生成...")
      connect(currentUrl, { preserveEvents: false })
    }
  }

  // Automatically clear task ID when done event arrives
  useEffect(() => {
    if (events.length > 0) {
      const lastEvent = events[events.length - 1]
      if (lastEvent.type === "done") {
        const timer = setTimeout(() => {
          setGenerationTaskId(null)
          setSseAction(null)
        }, 2000)
        return () => clearTimeout(timer)
      }
    }
  }, [events])

  // Poll backend task status if disconnected but task ID is still set
  useEffect(() => {
    if (isConnected || !generationTaskId) return

    let active = true
    const checkStatus = async () => {
      try {
        const task = await api.generate.taskStatus(projectId, generationTaskId)
        if (!active) return
        if (task && (task.status === "done" || task.status === "failed" || task.status === "cancelled")) {
          // Task completed in the background
          setGenerationTaskId(null)
          setSseAction(null)
          if (task.status === "done") {
            toast.success("任务生成完成")
          } else {
            toast.error(`后台任务执行失败: ${task.message || "未知原因"}`)
          }
        }
      } catch (err) {
        console.error("Failed to query task status:", err)
      }
    }

    // Initial check
    checkStatus()

    // Poll every 3 seconds
    const interval = setInterval(checkStatus, 3000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [isConnected, generationTaskId, projectId])


  return {
    generationTaskId, setGenerationTaskId,
    generationStopping, setGenerationStopping,
    sseAction, setSseAction,
    events, isConnected, sseError,
    generationChapterCount, setGenerationChapterCount,
    generationWordCount, setGenerationWordCount,
    batchChapterCount, setBatchChapterCount,
    enableBrainstorming, setEnableBrainstorming,
    generationTaskLabel, generationProgress, generationRecovering, hasError, generationStepMeta,
    handleStopGeneration, handleRetryGeneration,
    startTask, stopSse
  }
}
