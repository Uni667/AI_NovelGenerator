"use client"

import * as React from "react"
import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, X, Loader2, Sparkles, Minimize2, Maximize2, RefreshCw } from "lucide-react"

interface FloatingToolbarProps {
  x: number
  y: number
  visible: boolean
  onClose: () => void
  onSubmit: (instruction: string) => void
  isSubmitting?: boolean
}

const QUICK_ACTIONS = [
  { label: "润色", prompt: "请润色这段文字，使其更流畅优美", icon: Sparkles },
  { label: "扩写", prompt: "请扩写这段文字，增加细节描写", icon: Maximize2 },
  { label: "精简", prompt: "请精简这段文字，保留核心信息", icon: Minimize2 },
  { label: "改写", prompt: "请改写这段文字，换个表达方式", icon: RefreshCw },
] as const

export function FloatingToolbar({
  x,
  y,
  visible,
  onClose,
  onSubmit,
  isSubmitting = false
}: FloatingToolbarProps) {
  const [instruction, setInstruction] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const dragStartRef = useRef<{ startX: number; startY: number; initialOffsetX: number; initialOffsetY: number } | null>(null)

  // Reset drag offset when parent position changes
  useEffect(() => {
    setDragOffset({ x: 0, y: 0 })
  }, [x, y])

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return
    const target = e.target as HTMLElement
    if (target.closest("button") || target.closest("input")) return

    dragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialOffsetX: dragOffset.x,
      initialOffsetY: dragOffset.y
    }

    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleMouseUp)
    e.preventDefault()
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (!dragStartRef.current) return
    const dx = e.clientX - dragStartRef.current.startX
    const dy = e.clientY - dragStartRef.current.startY
    setDragOffset({
      x: dragStartRef.current.initialOffsetX + dx,
      y: dragStartRef.current.initialOffsetY + dy
    })
  }

  const handleMouseUp = () => {
    dragStartRef.current = null
    document.removeEventListener("mousemove", handleMouseMove)
    document.removeEventListener("mouseup", handleMouseUp)
  }

  useEffect(() => {
    if (visible && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [visible])

  useEffect(() => {
    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
    }
  }, [])

  if (!visible) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!instruction.trim() || isSubmitting) return
    onSubmit(instruction)
    setInstruction("")
  }

  const handleQuickAction = (prompt: string) => {
    onSubmit(prompt)
  }

  return (
    <div
      className="absolute z-50 flex flex-col gap-2 p-2.5 rounded-xl border border-white/10 bg-black/70 backdrop-blur-xl shadow-2xl animate-in fade-in zoom-in-95 duration-200 min-w-[320px]"
      style={{
        left: Math.max(10, x + dragOffset.x),
        top: Math.max(10, y + dragOffset.y),
        transform: 'translate(-50%, calc(-100% - 12px))',
      }}
    >
      {/* 顶部提示 */}
      <div 
        onMouseDown={handleMouseDown} 
        className="flex items-center justify-between px-1 cursor-move select-none"
      >
        <span className="text-[10px] text-gray-500">选中文本 — 选择操作方式：</span>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={onClose}
          disabled={isSubmitting}
          className="h-6 w-6 p-0 hover:bg-red-500/20 hover:text-red-400 text-gray-500"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* 快捷操作 */}
      <div className="flex items-center gap-1.5">
        {QUICK_ACTIONS.map(action => {
          const Icon = action.icon
          return (
            <button
              key={action.label}
              type="button"
              disabled={isSubmitting}
              onClick={() => handleQuickAction(action.prompt)}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11px] font-medium
                bg-white/5 hover:bg-white/15 text-gray-300 hover:text-white
                transition-colors disabled:opacity-40"
            >
              <Icon className="h-3 w-3" />
              {action.label}
            </button>
          )
        })}
      </div>

      {/* 分隔 */}
      <div className="flex items-center gap-2">
        <div className="h-px flex-1 bg-white/5" />
        <span className="text-[9px] text-gray-600">或自定义指令</span>
        <div className="h-px flex-1 bg-white/5" />
      </div>

      {/* 自定义输入 */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <Input
          ref={inputRef}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="输入具体修改要求…"
          className="flex-1 h-8 bg-black/40 border-white/10 text-sm focus-visible:ring-1 focus-visible:ring-emerald-500 placeholder:text-gray-600"
          disabled={isSubmitting}
        />
        <Button
          type="submit"
          size="sm"
          disabled={!instruction.trim() || isSubmitting}
          className="h-8 px-3 bg-emerald-600 hover:bg-emerald-500 text-white shrink-0"
          title="发送指令改写选中文本"
        >
          {isSubmitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" />
          )}
        </Button>
      </form>
    </div>
  )
}
