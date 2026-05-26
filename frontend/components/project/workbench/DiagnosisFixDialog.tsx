"use client"

import React, { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Loader2, CheckCircle, XCircle, FileText, Download, AlertCircle } from "lucide-react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { ScrollArea } from "@/components/ui/scroll-area"

interface DiagnosisFixDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  chapterContent: string
  diagnosis: string
  selectedIssues: string[]
  projectId: string
  chapterNumber: number
  /** Called when user accepts the fix — passes the optimized text back */
  onApply: (optimizedContent: string) => void
}

type FixState = "idle" | "generating" | "preview" | "applied" | "error"

export function DiagnosisFixDialog({
  open,
  onOpenChange,
  chapterContent,
  diagnosis,
  selectedIssues,
  projectId,
  chapterNumber,
  onApply,
}: DiagnosisFixDialogProps) {
  const [state, setState] = useState<FixState>("idle")
  const [optimizedContent, setOptimizedContent] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  // Reset on open
  React.useEffect(() => {
    if (open) {
      setState("idle")
      setOptimizedContent("")
      setErrorMessage("")
    }
  }, [open])

  const handleGenerateFix = async () => {
    if (!chapterContent.trim()) {
      toast.error("当前章节正文为空，请先生成或输入正文。")
      return
    }
    if (!diagnosis.trim()) {
      toast.error("请先生成章节诊断报告，再根据诊断进行优化。")
      return
    }

    setState("generating")
    try {
      const res = await api.platform.diagnoseAndFix(projectId, {
        chapter_number: chapterNumber,
        chapter_content: chapterContent,
        diagnosis,
        selected_issues: selectedIssues,
      })
      
      // Handle SSE response
      if (res.content) {
        setOptimizedContent(res.content)
        setState("preview")
      } else if (res.diagnosis) {
        setOptimizedContent(res.diagnosis)
        setState("preview")
      } else {
        // Try to read as SSE stream
        const text = await new Response(res).text()
        const lines = text.split("\n")
        let content = ""
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6))
              if (data.content) content = data.content
            } catch {}
          }
        }
        if (content) {
          setOptimizedContent(content)
          setState("preview")
        } else {
          throw new Error("响应中没有优化内容")
        }
      }
    } catch (e) {
      setErrorMessage((e as Error).message || "优化失败")
      setState("error")
      toast.error("优化失败，请稍后重试")
    }
  }

  const handleApply = () => {
    if (optimizedContent) {
      onApply(optimizedContent)
      setState("applied")
      toast.success("已根据诊断优化本章")
      onOpenChange(false)
    }
  }

  const severityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "bg-red-500/10 text-red-400 border-red-500/20"
      case "high": return "bg-orange-500/10 text-orange-400 border-orange-500/20"
      case "medium": return "bg-amber-500/10 text-amber-400 border-amber-500/20"
      default: return "bg-blue-500/10 text-blue-400 border-blue-500/20"
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (state !== "generating") onOpenChange(v) }}>
      <DialogContent className="max-w-3xl w-[90vw] h-[80vh] bg-background/95 backdrop-blur-xl border-border/60 p-0 rounded-2xl flex flex-col">
        <DialogHeader className="px-5 pt-5 pb-3 shrink-0 border-b border-border/20">
          <DialogTitle className="text-base font-bold flex items-center gap-2">
            <FileText className="h-4.5 w-4.5 text-primary" />
            根据诊断优化本章
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            第 {chapterNumber} 章 • 已选中 {selectedIssues.length || "全部"} 个优化项
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0 flex flex-col p-5 gap-4 overflow-hidden">
          {state === "idle" && (
            <div className="flex flex-col items-center justify-center flex-1 text-center">
              <AlertCircle className="h-10 w-10 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">点击下方按钮开始生成优化版本</p>
              <p className="text-xs text-muted-foreground/60 mt-1">AI 将根据诊断报告对本章进行针对性优化，保留原剧情和人物</p>
            </div>
          )}

          {state === "generating" && (
            <div className="flex flex-col items-center justify-center flex-1 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
              <p className="text-sm font-medium">正在根据诊断优化本章...</p>
              <p className="text-xs text-muted-foreground mt-1">AI 正在分析诊断报告并生成优化版本</p>
            </div>
          )}

          {state === "preview" && (
            <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Original */}
              <div className="flex flex-col min-h-0">
                <div className="flex items-center gap-2 mb-2 shrink-0">
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-muted/30">原文</Badge>
                  <span className="text-[10px] text-muted-foreground">{chapterContent.length} 字</span>
                </div>
                <ScrollArea className="flex-1 rounded-lg border border-border/40 bg-background/20 p-3">
                  <pre className="text-xs font-serif leading-relaxed whitespace-pre-wrap font-sans">{chapterContent}</pre>
                </ScrollArea>
              </div>
              {/* Optimized */}
              <div className="flex flex-col min-h-0">
                <div className="flex items-center gap-2 mb-2 shrink-0">
                  <Badge variant="default" className="text-[10px] px-1.5 py-0 bg-emerald-500/10 text-emerald-400 border-emerald-500/20">优化后</Badge>
                  <span className="text-[10px] text-muted-foreground">{optimizedContent.length} 字</span>
                </div>
                <ScrollArea className="flex-1 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <pre className="text-xs font-serif leading-relaxed whitespace-pre-wrap font-sans">{optimizedContent}</pre>
                </ScrollArea>
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="flex flex-col items-center justify-center flex-1 text-center">
              <XCircle className="h-8 w-8 text-destructive mb-3" />
              <p className="text-sm font-medium text-destructive">优化失败</p>
              <p className="text-xs text-muted-foreground mt-1">{errorMessage || "请稍后重试"}</p>
            </div>
          )}
        </div>

        <DialogFooter className="px-5 pb-5 pt-3 shrink-0 border-t border-border/20 flex items-center gap-2 justify-end">
          {state === "idle" && (
            <>
              <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} className="h-8 text-xs">
                取消
              </Button>
              <Button size="sm" onClick={handleGenerateFix} className="h-8 text-xs">
                <Download className="h-3.5 w-3.5 mr-1.5" />
                生成优化版本
              </Button>
            </>
          )}
          {state === "generating" && (
            <Button variant="outline" size="sm" disabled className="h-8 text-xs">
              <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              生成中...
            </Button>
          )}
          {state === "preview" && (
            <>
              <Button variant="outline" size="sm" onClick={() => { setState("idle"); setOptimizedContent("") }} className="h-8 text-xs">
                放弃修改
              </Button>
              <Button size="sm" onClick={handleApply} className="h-8 text-xs bg-emerald-600 hover:bg-emerald-500">
                <CheckCircle className="h-3.5 w-3.5 mr-1.5" />
                应用修改
              </Button>
            </>
          )}
          {state === "error" && (
            <>
              <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} className="h-8 text-xs">
                关闭
              </Button>
              <Button size="sm" onClick={handleGenerateFix} className="h-8 text-xs">
                重试
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
