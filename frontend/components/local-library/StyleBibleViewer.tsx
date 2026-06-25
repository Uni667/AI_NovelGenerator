import { useState, useEffect } from "react"
import { BookOpen, RefreshCw } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { api } from "@/lib/api-client"

interface StyleBibleViewerProps {
  bookId: string
}

export function StyleBibleViewer({ bookId }: StyleBibleViewerProps) {
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      if (!bookId) return
      setLoading(true)
      try {
        const res = await api.localLibrary.getEssence(bookId, "style_bible.md")
        setContent(typeof res === "string" ? res : (res.content || JSON.stringify(res)))
        setError("")
      } catch (e: any) {
        setError("尚未提炼风格圣经，或获取失败")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [bookId])

  return (
    <Card className="h-full flex flex-col border-border/40">
      <CardHeader className="py-3 px-4 border-b border-border/30 bg-muted/10">
        <CardTitle className="text-sm flex items-center gap-2 font-medium">
          <BookOpen className="w-4 h-4 text-purple-500" />
          风格圣经 (Style Bible)
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 overflow-hidden relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            <RefreshCw className="w-5 h-5 animate-spin" />
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground bg-muted/5">
            {error}
          </div>
        ) : (
          <ScrollArea className="h-[300px] w-full p-4">
            <pre className="text-xs font-mono whitespace-pre-wrap break-all">
              {content}
            </pre>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
