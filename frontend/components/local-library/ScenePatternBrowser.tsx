import { useState, useEffect } from "react"
import { Layers, RefreshCw } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api-client"

interface ScenePatternBrowserProps {
  bookId: string
}

export function ScenePatternBrowser({ bookId }: ScenePatternBrowserProps) {
  const [patterns, setPatterns] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      if (!bookId) return
      setLoading(true)
      try {
        const res = await api.localLibrary.getEssence(bookId, "scene_patterns.json")
        try {
          const text = typeof res === "string" ? res : (res.content || JSON.stringify(res))
          const parsed = typeof text === "string" ? JSON.parse(text) : text
          setPatterns(Array.isArray(parsed) ? parsed : [])
        } catch (e) {
          setError("解析场景模式 JSON 失败")
        }
      } catch (e: any) {
        setError("尚未提取场景模式，或获取失败")
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
          <Layers className="w-4 h-4 text-blue-500" />
          场景模式浏览器
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
        ) : patterns.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground bg-muted/5">
            暂无场景模式数据
          </div>
        ) : (
          <ScrollArea className="h-[300px] w-full p-4">
            <div className="space-y-4">
              {patterns.map((p, i) => (
                <div key={i} className="bg-muted/30 p-3 rounded-lg border border-border/50 text-sm">
                  <div className="font-semibold text-foreground mb-1 flex items-center justify-between">
                    <span>{p.pattern_name || `模式 ${i + 1}`}</span>
                    <Badge variant="outline" className="text-[10px] font-normal">
                      {p.category || "通用"}
                    </Badge>
                  </div>
                  <div className="text-muted-foreground mt-2 leading-relaxed">
                    {p.description || "无描述"}
                  </div>
                  {p.key_elements && p.key_elements.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-foreground mb-1">关键要素:</div>
                      <ul className="list-disc pl-4 text-muted-foreground text-xs space-y-1">
                        {p.key_elements.map((el: string, j: number) => (
                          <li key={j}>{el}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
