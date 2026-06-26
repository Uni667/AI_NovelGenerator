import { Book, FileText, Activity } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { LocalReferenceBook } from "@/lib/types"

interface BookListTableProps {
  books: LocalReferenceBook[]
  onViewBook: (book: LocalReferenceBook) => void
}

export function BookListTable({ books, onViewBook }: BookListTableProps) {
  if (books.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-background/30 rounded-xl border border-dashed border-border/50">
        <Book className="w-12 h-12 text-muted-foreground/30 mb-4" />
        <h3 className="text-lg font-medium text-foreground">暂无参考书籍</h3>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm text-center">
          请先在配置面板指定原文 txt 文件夹并授予读写权限，然后执行「全量扫描」。
        </p>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending": return <Badge variant="secondary">等待解析</Badge>
      case "parsing": return <Badge className="bg-blue-500/20 text-blue-500 hover:bg-blue-500/30">解析中</Badge>
      case "parsed": return <Badge className="bg-green-500/20 text-green-500 hover:bg-green-500/30">已解析</Badge>
      case "absorbing": return <Badge className="bg-amber-500/20 text-amber-500 hover:bg-amber-500/30 animate-pulse">吸收中</Badge>
      case "absorbed": return <Badge className="bg-primary/20 text-primary hover:bg-primary/30">已吸收</Badge>
      case "error": return <Badge variant="destructive">错误</Badge>
      default: return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="rounded-xl border border-border/40 overflow-hidden bg-card/30 backdrop-blur-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-muted-foreground bg-secondary/50 border-b border-border/40">
            <tr>
              <th className="px-4 py-3 font-medium">书名</th>
              <th className="px-4 py-3 font-medium w-32">源文件</th>
              <th className="px-4 py-3 font-medium w-32">状态</th>
              <th className="px-4 py-3 font-medium w-32">更新时间</th>
              <th className="px-4 py-3 font-medium w-24 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/30">
            {books.map((b) => (
              <tr key={b.id} className="hover:bg-muted/30 transition-colors group">
                <td className="px-4 py-3">
                  <div className="font-medium text-foreground flex items-center gap-2">
                    <Book className="w-4 h-4 text-primary/70" />
                    {b.title}
                  </div>
                  {b.total_chapters > 0 && (
                    <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      共 {b.total_chapters} 章 · {Math.round((b.total_words || 0) / 10000)}万字
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  <div className="truncate max-w-[150px]" title={b.source_file_name}>
                    {b.source_file_name}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {getStatusBadge(b.parse_status)}
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs">
                  {(b.last_parsed_at || b.last_scanned_at) ? new Date(b.last_parsed_at || b.last_scanned_at!).toLocaleString() : "-"}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => onViewBook(b)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    查看详情
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
