"use client"

import { useState } from "react"
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
    
  const lastEvent = events[events.length - 1]
  const generationProgress = lastEvent?.type === "progress" ? (lastEvent.data.progress || 0) : 0
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
