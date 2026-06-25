import { useState, useEffect, useCallback } from "react"
import { AlertCircle, Check, X, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import { api } from "@/lib/api-client"

interface ChapterBoundaryReviewProps {
  bookId: string
}

export function ChapterBoundaryReview({ bookId }: ChapterBoundaryReviewProps) {
  const [chapters, setChapters] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState("")

  const loadChapters = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.localLibrary.listChapters(bookId)
      setChapters(res)
    } catch (e: any) {
      toast.error(e?.message || "无法加载章节信息")
    } finally {
      setLoading(false)
    }
  }, [bookId])

  useEffect(() => {
    loadChapters()
  }, [loadChapters])

  const handleUpdate = async (chapId: string) => {
    try {
      // Notice: we might just need to update the title or drop it if it's a false positive
      // For now, this is a placeholder for actual boundary editing API if it existed
      toast.success("暂不支持前端直接编辑边界（后端API未就绪），可直接重新解析")
      setEditingId(null)
    } catch (e: any) {
      toast.error("更新失败")
    }
  }

  return (
    <div className="bg-background/80 p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-medium">章节列表 ({chapters.length})</h4>
        <Button variant="ghost" size="sm" onClick={loadChapters} disabled={loading}>
          <RefreshCw className={`w-3 h-3 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          刷新
        </Button>
      </div>

      <div className="max-h-[300px] overflow-y-auto space-y-2 pr-2">
        {chapters.map((chap) => (
          <div key={chap.id} className="flex items-center justify-between p-2 rounded bg-card border border-border/50 text-sm">
            <div className="flex-1 min-w-0 pr-4">
              {editingId === chap.id ? (
                <Input 
                  value={editTitle} 
                  onChange={e => setEditTitle(e.target.value)}
                  className="h-7 text-sm px-2"
                />
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground w-10 shrink-0">#{chap.chapter_index}</span>
                  <span className="truncate font-medium" title={chap.title}>{chap.title}</span>
                  {chap.parse_confidence < 0.8 && (
                    <span className="flex items-center text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">
                      <AlertCircle className="w-3 h-3 mr-1" />
                      置信度低
                    </span>
                  )}
                </div>
              )}
            </div>
            
            <div className="shrink-0 flex items-center gap-1">
              <span className="text-xs text-muted-foreground mr-3 hidden sm:inline-block">
                {chap.word_count} 字
              </span>
              {editingId === chap.id ? (
                <>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-green-500" onClick={() => handleUpdate(chap.id)}>
                    <Check className="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => setEditingId(null)}>
                    <X className="w-3.5 h-3.5" />
                  </Button>
                </>
              ) : (
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => {
                  setEditingId(chap.id)
                  setEditTitle(chap.title)
                }}>
                  修改
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {chapters.length === 0 && !loading && (
        <div className="text-center py-6 text-sm text-muted-foreground">
          无章节数据，请先执行解析
        </div>
      )}
    </div>
  )
}
