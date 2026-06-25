"use client"

import { useEffect, useState } from "react"
import { CheckCircle, Plus, Trash2, BookOpen } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import type { ProjectReferenceBinding, LocalReferenceBook } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function LocalLibraryTab({ projectId }: { projectId: string }) {
  const [bindings, setBindings] = useState<ProjectReferenceBinding[]>([])
  const [availableBooks, setAvailableBooks] = useState<LocalReferenceBook[]>([])
  const [loading, setLoading] = useState(true)
  const [binding, setBinding] = useState(false)
  const [selectedBookId, setSelectedBookId] = useState<string>("")

  const loadData = async () => {
    setLoading(true)
    try {
      const [boundList, allBooks] = await Promise.all([
        api.projectBindings.list(projectId).catch(() => []),
        api.localLibrary.listBooks().catch(() => []),
      ])
      setBindings(boundList)
      setAvailableBooks(allBooks)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (projectId) {
      loadData()
    }
  }, [projectId])

  const handleBind = async () => {
    if (!selectedBookId) return
    setBinding(true)
    try {
      await api.projectBindings.bind(projectId, selectedBookId, { book_id: selectedBookId })
      toast.success("绑定成功")
      setSelectedBookId("")
      await loadData()
    } catch (e: any) {
      toast.error(e?.message || "绑定失败")
    } finally {
      setBinding(false)
    }
  }

  const handleUnbind = async (bookId: string) => {
    if (!confirm("确定解除这本参考书的绑定吗？")) return
    try {
      await api.projectBindings.unbind(projectId, bookId)
      toast.success("解绑成功")
      await loadData()
    } catch (e: any) {
      toast.error(e?.message || "解绑失败")
    }
  }

  const handleUpdate = async (bookId: string, updates: any) => {
    try {
      // 乐观更新 UI
      setBindings((prev) =>
        prev.map((item) => (item.book_id === bookId ? { ...item, ...updates } : item))
      )
      await api.projectBindings.update(projectId, bookId, updates)
    } catch (e: any) {
      toast.error(e?.message || "更新失败")
      await loadData() // 恢复原状
    }
  }

  const unboundBooks = availableBooks.filter(
    (b) => !bindings.find((bound) => bound.book_id === b.id)
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-border/40 pb-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 text-foreground">
            <BookOpen className="w-5 h-5 text-primary" /> 参考书库绑定
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            为当前小说绑定参考书籍。生成章节时，AI 将自动融合这几本书的写作手法与结构规则。
          </p>
        </div>

        <div className="flex gap-2 items-center">
          <Select value={selectedBookId} onValueChange={(v) => setSelectedBookId(v || "")}>
            <SelectTrigger className="w-[200px] h-9">
              <SelectValue placeholder="选择参考书..." />
            </SelectTrigger>
            <SelectContent>
              {unboundBooks.length === 0 ? (
                <div className="px-2 py-4 text-xs text-muted-foreground text-center">
                  暂无可绑定的参考书
                </div>
              ) : (
                unboundBooks.map((book) => (
                  <SelectItem key={book.id} value={book.id}>
                    {book.title}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            disabled={binding || !selectedBookId}
            onClick={handleBind}
            className="shadow-glow"
          >
            <Plus className="w-4 h-4 mr-1" />
            绑定
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-sm text-muted-foreground">正在读取参考书绑定...</div>
      ) : bindings.length ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {bindings.map((item) => {
            const bookInfo = availableBooks.find((b) => b.id === item.book_id)
            return (
              <Card key={item.id} className="glass-card">
                <CardHeader className="pb-3 border-b border-border/30 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      {bookInfo?.title || "未识别参考书"}
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground mt-1">
                      ID: {item.book_id}
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleUnbind(item.book_id)}
                    className="text-muted-foreground hover:text-destructive h-8 w-8"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </CardHeader>
                <CardContent className="pt-4 space-y-4 text-sm">
                  <div className="space-y-3 font-medium">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">启用绑定 (enabled)</span>
                      <Switch
                        checked={item.enabled}
                        onCheckedChange={(v) => handleUpdate(item.book_id, { enabled: v })}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">提取风格圣经规则 (use_style_bible)</span>
                      <Switch
                        checked={item.use_style_bible}
                        onCheckedChange={(v) => handleUpdate(item.book_id, { use_style_bible: v })}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">提取场景/爽点模板 (use_scene_patterns)</span>
                      <Switch
                        checked={item.use_scene_patterns}
                        onCheckedChange={(v) => handleUpdate(item.book_id, { use_scene_patterns: v })}
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">提取节奏控制规则 (use_pacing_rules)</span>
                      <Switch
                        checked={item.use_pacing_rules}
                        onCheckedChange={(v) => handleUpdate(item.book_id, { use_pacing_rules: v })}
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">人物弧光模型 (use_character_arcs)</span>
                      <Switch
                        checked={item.use_character_arcs}
                        onCheckedChange={(v) => handleUpdate(item.book_id, { use_character_arcs: v })}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">启用防照抄检测 (use_anti_copy_guard)</span>
                      <Switch
                        checked={item.use_anti_copy_guard}
                        onCheckedChange={(v) => handleUpdate(item.book_id, { use_anti_copy_guard: v })}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <div className="py-12 text-center text-sm text-muted-foreground border border-dashed border-border/50 rounded-lg">
          当前项目尚未绑定任何参考书。
        </div>
      )}
    </div>
  )
}
