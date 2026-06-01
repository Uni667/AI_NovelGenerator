"use client"
 
import { useState, useCallback, useEffect, useRef } from "react"
import { api } from "@/lib/api-client"
import { getToken } from "@/lib/auth"
import { toast } from "sonner"
import type { Chapter } from "@/lib/types"
import { useSSE } from "./use-sse"
import { useSearchParams } from "next/navigation"
 
export function useWorkbenchState(projectId: string) {
  const [selectedChapterNumber, setSelectedChapterNumber] = useState(1)
  const [chapterEditorContent, setChapterEditorContent] = useState("")
  const [chapterEditorLoading, setChapterEditorLoading] = useState(false)
  const [chapterEditorSaving, setChapterEditorSaving] = useState(false)
  
  const editorContentRef = useRef("")
  const loadedContentRef = useRef("")
  const activeChapterMetaRef = useRef<Chapter | null>(null)

  useEffect(() => {
    editorContentRef.current = chapterEditorContent
  }, [chapterEditorContent])
  const [isSyncing, setIsSyncing] = useState(false)
  const [activeChapterMeta, setActiveChapterMeta] = useState<Chapter | null>(null)
 
  // Layout states for directory/attributes and focus mode toggles
  const [layoutMode, setLayoutMode] = useState<'standard' | 'wide' | 'focus'>('standard')
  const [previousLayoutMode, setPreviousLayoutMode] = useState<'standard' | 'wide'>('standard')
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false)
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false)
  const [leftDrawerOpen, setLeftDrawerOpen] = useState(false)
  const [assistantDrawerOpen, setAssistantDrawerOpen] = useState(false)
  const [activeAssistantTool, setActiveAssistantTool] = useState("outline")
  const [fontSize, setFontSize] = useState(18)

  // Derived compatibility states
  const focusMode = layoutMode === "focus"
  const leftSidebarOpen = !leftPanelCollapsed
  const rightPanelOpen = !rightPanelCollapsed

  const setFocusMode = useCallback((val: boolean | ((prev: boolean) => boolean)) => {
    setLayoutMode(prev => {
      const target = typeof val === 'function' ? val(prev === 'focus') : val
      if (target) {
        setPreviousLayoutMode(prev === 'focus' ? 'standard' : prev)
        return 'focus'
      } else {
        return previousLayoutMode || 'standard'
      }
    })
  }, [previousLayoutMode])

  const setLeftSidebarOpen = useCallback((val: boolean | ((prev: boolean) => boolean)) => {
    setLeftPanelCollapsed(prev => {
      const open = typeof val === 'function' ? val(!prev) : val
      return !open
    })
  }, [])

  const setRightPanelOpen = useCallback((val: boolean | ((prev: boolean) => boolean)) => {
    setRightPanelCollapsed(prev => {
      const open = typeof val === 'function' ? val(!prev) : val
      return !open
    })
  }, [])

  // Sync states from localStorage safely on mount to prevent SSR warnings
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedMode = localStorage.getItem("ai-novel-workbench-layout-mode") as 'standard' | 'wide' | 'focus'
      if (savedMode && ['standard', 'wide', 'focus'].includes(savedMode)) {
        setLayoutMode(savedMode)
        if (savedMode !== 'focus') {
          setPreviousLayoutMode(savedMode)
        }
      }

      const savedFontSize = localStorage.getItem("ai-novel-editor-font-size")
      if (savedFontSize) {
        setFontSize(Number(savedFontSize))
      }

      const savedLeftCollapsed = localStorage.getItem("ai-novel-left-panel-collapsed")
      if (savedLeftCollapsed) {
        setLeftPanelCollapsed(savedLeftCollapsed === "true")
      }

      const savedRightCollapsed = localStorage.getItem("ai-novel-right-panel-collapsed")
      if (savedRightCollapsed) {
        setRightPanelCollapsed(savedRightCollapsed === "true")
      }
    }
  }, [])

  const searchParams = useSearchParams()
  useEffect(() => {
    if (searchParams) {
      const chIdStr = searchParams.get("chapterId")
      const source = searchParams.get("source")
      if (chIdStr && source === "visualizer") {
        const chNum = parseInt(chIdStr, 10)
        if (!isNaN(chNum)) {
          setSelectedChapterNumber(chNum)
        }
      }
    }
  }, [searchParams, setSelectedChapterNumber])

  // Save states to localStorage and toggle focus-mode class on documentElement
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("ai-novel-workbench-layout-mode", layoutMode)
    }
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("focus-mode", layoutMode === "focus")
    }
    return () => {
      if (typeof document !== "undefined") {
        document.documentElement.classList.remove("focus-mode")
      }
    }
  }, [layoutMode])

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("ai-novel-editor-font-size", String(fontSize))
    }
  }, [fontSize])

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("ai-novel-left-panel-collapsed", String(leftPanelCollapsed))
    }
  }, [leftPanelCollapsed])

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("ai-novel-right-panel-collapsed", String(rightPanelCollapsed))
    }
  }, [rightPanelCollapsed])
 
  // Selection and assistant states
  const [selectedText, setSelectedText] = useState("")
  const [toolbarState, setToolbarState] = useState({ x: 0, y: 0, visible: false, startIndex: 0, endIndex: 0 })
  const [isRewriting, setIsRewriting] = useState(false)
  const [showReference, setShowReference] = useState(false)
  const [isReferenceExpanded, setIsReferenceExpanded] = useState(false)
  const [assistantMode, setAssistantMode] = useState<"diagnose" | "rewrite" | "chat">("diagnose")
  const [sidebarTab, setSidebarTab] = useState<string>("outline")
  const [selectionDiagnosis, setSelectionDiagnosis] = useState("")
  const [selectionDiagLoading, setSelectionDiagLoading] = useState(false)
  const [rewritePreview, setRewritePreview] = useState("")
  const [customRewriteInstruction, setCustomRewriteInstruction] = useState("")
  const [assistantChatHistory, setAssistantChatHistory] = useState<Array<{role: 'user' | 'assistant'; content: string}>>([])
  const [assistantQuestion, setAssistantQuestion] = useState("")
  const [assistantChatLoading, setAssistantChatLoading] = useState(false)
 
  // Chat History & loading states for askAi
  const [chatHistory, setChatHistory] = useState<Array<{role: 'user' | 'assistant'; content: string}>>([])
  const [aiQuestion, setAiQuestion] = useState("")
  const [askAiLoading, setAskAiLoading] = useState(false)
 
  // Instantiating SSE Hooks
  const diagSse = useSSE()
  const assistantChatSse = useSSE()
  const askAiSse = useSSE()
 
  // Clear previous assistant states when a new text is selected
  useEffect(() => {
    setSelectionDiagnosis("")
    setRewritePreview("")
    setAssistantChatHistory([])
    setCustomRewriteInstruction("")
  }, [selectedText])
 
  // Clear chat history when selected chapter changes
  useEffect(() => {
    setChatHistory([])
  }, [selectedChapterNumber])
 
  // Watch for SSE error states directly to reset loading indicators and alert user
  useEffect(() => {
    if (diagSse.error) {
      setSelectionDiagLoading(false)
      toast.error(diagSse.error)
    }
  }, [diagSse.error])
 
  useEffect(() => {
    if (assistantChatSse.error) {
      setAssistantChatLoading(false)
      toast.error(assistantChatSse.error)
    }
  }, [assistantChatSse.error])
 
  useEffect(() => {
    if (askAiSse.error) {
      setAskAiLoading(false)
      toast.error(askAiSse.error)
    }
  }, [askAiSse.error])
 
  // Listen to Selection Diagnosis SSE stream updates
  useEffect(() => {
    if (diagSse.events.length === 0) return
    const lastEvent = diagSse.events[diagSse.events.length - 1]
    if (lastEvent.type === "partial" && lastEvent.data?.content) {
      setSelectionDiagnosis(prev => prev + lastEvent.data.content)
    } else if (lastEvent.type === "done") {
      setSelectionDiagLoading(false)
    } else if (lastEvent.type === "error") {
      setSelectionDiagLoading(false)
    }
  }, [diagSse.events])
 
  // Listen to Assistant Chat SSE stream updates
  useEffect(() => {
    if (assistantChatSse.events.length === 0) return
    const lastEvent = assistantChatSse.events[assistantChatSse.events.length - 1]
    if (lastEvent.type === "partial" && lastEvent.data?.content) {
      setAssistantChatHistory(prev => {
        const updated = [...prev]
        if (updated.length > 0) {
          const last = updated[updated.length - 1]
          if (last.role === "assistant") {
            last.content = last.content + lastEvent.data.content
          }
        }
        return updated
      })
    } else if (lastEvent.type === "done") {
      setAssistantChatLoading(false)
    } else if (lastEvent.type === "error") {
      setAssistantChatLoading(false)
    }
  }, [assistantChatSse.events])
 
  // Listen to Ask AI SSE stream updates
  useEffect(() => {
    if (askAiSse.events.length === 0) return
    const lastEvent = askAiSse.events[askAiSse.events.length - 1]
    if (lastEvent.type === "partial" && lastEvent.data?.content) {
      setChatHistory(prev => {
        const updated = [...prev]
        if (updated.length > 0) {
          const last = updated[updated.length - 1]
          if (last.role === "assistant") {
            last.content = last.content + lastEvent.data.content
          }
        }
        return updated
      })
    } else if (lastEvent.type === "done") {
      setAskAiLoading(false)
    } else if (lastEvent.type === "error") {
      setAskAiLoading(false)
    }
  }, [askAiSse.events])
 
  const loadWorkbenchChapter = useCallback(async (num: number, force = false) => {
    // If not forced and there are unsaved changes, auto-save first!
    if (!force && editorContentRef.current && loadedContentRef.current && editorContentRef.current !== loadedContentRef.current && activeChapterMetaRef.current) {
      try {
        await api.chapters.update(projectId, activeChapterMetaRef.current.chapter_number, { content: editorContentRef.current })
      } catch (e) {
        console.error("Auto-saving prior chapter failed:", e)
      }
    }
    
    setChapterEditorLoading(true)
    try {
      const res = await api.chapters.get(projectId, num)
      const content = res.content || ""
      setChapterEditorContent(content)
      editorContentRef.current = content
      loadedContentRef.current = content
      setActiveChapterMeta(res.meta || null)
      activeChapterMetaRef.current = res.meta || null
    } catch (error) {
      toast.error((error as Error).message || "获取章节内容失败")
      setChapterEditorContent("")
      editorContentRef.current = ""
      loadedContentRef.current = ""
      setActiveChapterMeta(null)
      activeChapterMetaRef.current = null
    } finally {
      setChapterEditorLoading(false)
    }
  }, [projectId])
 
  const saveWorkbenchChapter = useCallback(async (status?: Chapter["status"]): Promise<Chapter | null> => {
    setChapterEditorSaving(true)
    try {
      const res = await api.chapters.update(projectId, selectedChapterNumber, { content: chapterEditorContent, status })
      const meta = res.meta || null
      if (meta) {
        setActiveChapterMeta(meta)
        activeChapterMetaRef.current = meta
      }
      loadedContentRef.current = chapterEditorContent
      toast.success("保存成功")
      return meta
    } catch (error) {
      toast.error((error as Error).message || "保存草稿失败")
      return null
    } finally {
      setChapterEditorSaving(false)
    }
  }, [projectId, selectedChapterNumber, chapterEditorContent])
 
  // Selection Diagnosis SSE connection
  const handleDiagnoseSelection = useCallback(async (textToDiagnose?: string) => {
    const text = textToDiagnose || selectedText
    if (!text.trim() || diagSse.isConnected) return
    setSelectionDiagnosis("")
    setSelectionDiagLoading(true)
    setAssistantMode("diagnose")
 
    const questionEscaped = encodeURIComponent("请对此段文本进行详细的文风和节奏诊断，指出其中有所欠缺或不足的位置，说明为什么要优化它，并给出优化改进的具体方向。")
    const selectedTextEscaped = encodeURIComponent(text)
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    const url = `${apiBase}/api/v1/projects/${projectId}/chapters/${selectedChapterNumber}/ask-ai?question=${questionEscaped}&selected_text=${selectedTextEscaped}`
    diagSse.connect(url)
  }, [selectedText, projectId, selectedChapterNumber, diagSse])
 
  // Selection Rewrite Handler
  const handleRewriteSelection = useCallback(async (instruction: string, textToRewrite?: string) => {
    const text = textToRewrite || selectedText
    if (!text.trim() || isRewriting) return
    setIsRewriting(true)
    setRewritePreview("")
    setAssistantMode("rewrite")
 
    const contextBefore = chapterEditorContent.substring(Math.max(0, toolbarState.startIndex - 500), toolbarState.startIndex)
    const contextAfter = chapterEditorContent.substring(toolbarState.endIndex, Math.min(chapterEditorContent.length, toolbarState.endIndex + 500))
 
    try {
      const response = await fetch(api.interactive.getRewriteUrl(projectId), {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getToken()}`
        },
        body: JSON.stringify({
          context_before: contextBefore,
          selected_text: text,
          context_after: contextAfter,
          user_instruction: instruction
        })
      })
 
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "请求重写失败")
      }
      if (!response.body) throw new Error("没有流返回")
 
      const reader = response.body.getReader()
      const decoder = new TextDecoder("utf-8")
      let rewrittenText = ""
      let buffer = ""
 
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
 
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""
 
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const dataStr = JSON.parse(line.substring(6))
              const payload = typeof dataStr === 'string' ? JSON.parse(dataStr) : dataStr
              if (payload.content) {
                rewrittenText = payload.content
                setRewritePreview(rewrittenText)
              }
            } catch {}
          }
        }
      }
      toast.success("改写生成完成！")
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setIsRewriting(false)
    }
  }, [selectedText, projectId, isRewriting, chapterEditorContent, toolbarState])
 
  // Apply Rewrite back to Editor
  const handleApplyRewrite = useCallback(() => {
    if (!rewritePreview) return
    setChapterEditorContent(prev => {
      return prev.substring(0, toolbarState.startIndex) + rewritePreview + prev.substring(toolbarState.endIndex)
    })
    setSelectedText(rewritePreview)
    setToolbarState(prev => ({
      ...prev,
      endIndex: prev.startIndex + rewritePreview.length
    }))
    setRewritePreview("")
    toast.success("已应用改写！")
  }, [rewritePreview, toolbarState])
 
  // Q&A Coach Chat for Selection
  const handleAssistantChat = useCallback((questionText: string, textToRef?: string) => {
    const text = textToRef || selectedText
    if (!questionText.trim() || !text.trim() || assistantChatSse.isConnected) return
 
    const userMsg = { role: 'user' as const, content: questionText }
    setAssistantChatHistory(prev => [...prev, userMsg, { role: 'assistant' as const, content: "" }])
    setAssistantQuestion("")
    setAssistantChatLoading(true)
    setAssistantMode("chat")
 
    const questionEscaped = encodeURIComponent(questionText)
    const selectedTextEscaped = encodeURIComponent(text)
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    const url = `${apiBase}/api/v1/projects/${projectId}/chapters/${selectedChapterNumber}/ask-ai?question=${questionEscaped}&selected_text=${selectedTextEscaped}`
    assistantChatSse.connect(url)
  }, [selectedText, projectId, selectedChapterNumber, assistantChatSse])
 
  // Ask AI handler (Main)
  const handleAskAi = useCallback(async (questionText: string, textToRef?: string) => {
    if (!questionText.trim() || askAiSse.isConnected) return
    
    // Add user question to history
    const userMsg = { role: 'user' as const, content: questionText }
    setChatHistory(prev => [...prev, userMsg, { role: 'assistant' as const, content: "" }])
    setAiQuestion("")
    setAskAiLoading(true)
    
    const text = textToRef || selectedText
    const questionEscaped = encodeURIComponent(questionText)
    const selectedTextEscaped = text ? encodeURIComponent(text) : ""
    
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    const url = `${apiBase}/api/v1/projects/${projectId}/chapters/${selectedChapterNumber}/ask-ai?question=${questionEscaped}&selected_text=${selectedTextEscaped}`
    askAiSse.connect(url)
  }, [selectedText, projectId, selectedChapterNumber, askAiSse])
 
  return {
    selectedChapterNumber, setSelectedChapterNumber,
    chapterEditorContent, setChapterEditorContent,
    chapterEditorLoading,
    chapterEditorSaving,
    isSyncing, setIsSyncing,
    activeChapterMeta, setActiveChapterMeta,
    loadWorkbenchChapter,
    saveWorkbenchChapter,
    focusMode, setFocusMode,
    leftSidebarOpen, setLeftSidebarOpen,
    rightPanelOpen, setRightPanelOpen,
    layoutMode, setLayoutMode,
    previousLayoutMode, setPreviousLayoutMode,
    leftPanelCollapsed, setLeftPanelCollapsed,
    rightPanelCollapsed, setRightPanelCollapsed,
    leftDrawerOpen, setLeftDrawerOpen,
    assistantDrawerOpen, setAssistantDrawerOpen,
    activeAssistantTool, setActiveAssistantTool,
    fontSize, setFontSize,
    selectedText, setSelectedText,
    toolbarState, setToolbarState,
    isRewriting, setIsRewriting,
    showReference, setShowReference,
    isReferenceExpanded, setIsReferenceExpanded,
    assistantMode, setAssistantMode,
    sidebarTab, setSidebarTab,
    selectionDiagnosis, setSelectionDiagnosis,
    selectionDiagLoading, setSelectionDiagLoading,
    rewritePreview, setRewritePreview,
    customRewriteInstruction, setCustomRewriteInstruction,
    assistantChatHistory, setAssistantChatHistory,
    assistantQuestion, setAssistantQuestion,
    assistantChatLoading, setAssistantChatLoading,
    
    chatHistory, setChatHistory,
    aiQuestion, setAiQuestion,
    askAiLoading, setAskAiLoading,
    diagSse, assistantChatSse, askAiSse,
    
    handleDiagnoseSelection,
    handleRewriteSelection,
    handleApplyRewrite,
    handleAssistantChat,
    handleAskAi
  }
}
