import { useState } from "react"
import { Book, FileText, Play, Eye, GitPullRequest, Search, FileJson } from "lucide-react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { LocalReferenceBook } from "@/lib/types"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { ChapterBoundaryReview } from "./ChapterBoundaryReview"
import { AbsorptionProgressPanel } from "./AbsorptionProgressPanel"

interface BookDetailDrawerProps {
  book: LocalReferenceBook | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onRefreshList: () => void
  onViewEssence: (bookId: string) => void
}

export function BookDetailDrawer({ book, open, onOpenChange, onRefreshList, onViewEssence }: BookDetailDrawerProps) {
  const [parsing, setParsing] = useState(false)
  const [showReview, setShowReview] = useState(false)
  
  if (!book) return null

  const handleParse = async () => {
    setParsing(true)
    try {
      await api.localLibrary.parseBook(book.id)
      toast.success("解析任务已触发，请稍后刷新查看")
      onRefreshList()
    } catch (e: any) {
      toast.error(e?.message || "解析触发失败")
    } finally {
      setParsing(false)
    }
  }

  const handleAbsorptionUpdate = () => {
    onRefreshList()
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[90vw] sm:max-w-[600px] sm:w-[600px] overflow-y-auto h-full p-0 flex flex-col">
        <div className="bg-muted/30 p-6 border-b border-border/40">
          <SheetHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <SheetTitle className="text-2xl flex items-center gap-2">
                  <Book className="w-6 h-6 text-primary" />
                  {book.title}
                </SheetTitle>
                <SheetDescription className="mt-2 text-sm">
                  {book.source_file_path}
                </SheetDescription>
              </div>
              <Badge variant="outline" className="shrink-0 text-sm py-1">
                {book.parse_status}
              </Badge>
            </div>
          </SheetHeader>
          
          <div className="flex flex-wrap gap-4 mt-6">
            <div className="bg-background/50 px-4 py-2 rounded-lg border border-border/40">
              <div className="text-xs text-muted-foreground mb-1">文件大小</div>
              <div className="font-medium text-sm">{(book.source_file_size / 1024 / 1024).toFixed(2)} MB</div>
            </div>
            {((book as any).chapter_count || 0) > 0 && (
              <div className="bg-background/50 px-4 py-2 rounded-lg border border-border/40">
                <div className="text-xs text-muted-foreground mb-1">已识别章节</div>
                <div className="font-medium text-sm">{(book as any).chapter_count} 章</div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 p-6 space-y-8 overflow-y-auto">
          {/* Section 1: Parsing */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium flex items-center gap-2">
              <Search className="w-5 h-5 text-primary/70" />
              1. 结构解析
            </h3>
            <p className="text-sm text-muted-foreground">
              识别小说 txt 文件中的卷、章节边界。需要完成解析后才能进行吸收。
            </p>
            <div className="flex flex-wrap gap-3">
              <Button onClick={handleParse} disabled={parsing || book.parse_status === 'parsing'}>
                {parsing ? "触发中..." : (book.parse_status === 'new' || book.parse_status === 'failed' ? "开始解析" : "重新解析")}
              </Button>
              {((book as any).chapter_count || 0) > 0 && (
                <Button variant="secondary" onClick={() => setShowReview(!showReview)}>
                  <GitPullRequest className="w-4 h-4 mr-2" />
                  查看/修正边界
                </Button>
              )}
            </div>
            
            {showReview && (
              <div className="mt-4 border border-border/40 rounded-xl overflow-hidden">
                <ChapterBoundaryReview bookId={book.id} />
              </div>
            )}
          </div>

          {/* Section 2: Absorption */}
          {book.parse_status !== 'new' && book.parse_status !== 'parsing' && ((book as any).chapter_count || 0) > 0 && (
            <div className="space-y-4 pt-4 border-t border-border/40">
              <h3 className="text-lg font-medium flex items-center gap-2">
                <Play className="w-5 h-5 text-amber-500/70" />
                2. 吸收转化
              </h3>
              <p className="text-sm text-muted-foreground">
                提取章节摘要、分析剧情结构、提炼风格圣经和场景模式。
              </p>
              
              <AbsorptionProgressPanel 
                bookId={book.id} 
                bookStatus={book.parse_status}
                onStatusChange={handleAbsorptionUpdate} 
              />
            </div>
          )}
          
          {/* Section 3: View Essence */}
          {['absorbed', 'absorbing'].includes(book.parse_status) && (
            <div className="space-y-4 pt-4 border-t border-border/40">
              <h3 className="text-lg font-medium flex items-center gap-2">
                <FileJson className="w-5 h-5 text-green-500/70" />
                3. 精华结果
              </h3>
              <p className="text-sm text-muted-foreground">
                查看已提炼的风格文件、场景模板和摘要。
              </p>
              <Button variant="default" className="bg-green-600 hover:bg-green-700" onClick={() => onViewEssence(book.id)}>
                <Eye className="w-4 h-4 mr-2" />
                进入精华文件视图
              </Button>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
