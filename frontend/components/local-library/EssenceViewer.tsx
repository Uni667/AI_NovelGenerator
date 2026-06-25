import { useState, useEffect, useCallback } from "react"
import { FileJson, RefreshCw, ChevronRight, FileText } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

interface EssenceViewerProps {
  bookId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EssenceViewer({ bookId, open, onOpenChange }: EssenceViewerProps) {
  const [manifest, setManifest] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>("")
  const [contentLoading, setContentLoading] = useState(false)

  const loadManifest = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await api.localLibrary.getEssenceManifest(bookId)
      setManifest(res)
    } catch (e: any) {
      toast.error("无法加载精华索引，可能是尚未生成")
    } finally {
      setLoading(false)
    }
  }, [bookId, open])

  useEffect(() => {
    loadManifest()
  }, [loadManifest])

  const handleSelectFile = async (fileKey: string) => {
    setSelectedFile(fileKey)
    setContentLoading(true)
    try {
      const res = await api.localLibrary.getEssence(bookId, fileKey)
      // res could be { content: string } or string depending on backend
      setFileContent(typeof res === "string" ? res : (res.content || JSON.stringify(res)))
    } catch (e: any) {
      toast.error("读取文件失败")
      setFileContent("")
    } finally {
      setContentLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-[90vw] h-[85vh] p-0 flex flex-col gap-0 overflow-hidden">
        <DialogHeader className="p-4 border-b border-border/40 bg-muted/20">
          <DialogTitle className="flex items-center gap-2">
            <FileJson className="w-5 h-5 text-primary" />
            已提取精华文件
            <Button variant="ghost" size="icon" className="h-6 w-6 ml-2" onClick={loadManifest} disabled={loading}>
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar file list */}
          <div className="w-1/3 min-w-[200px] border-r border-border/40 bg-muted/10 flex flex-col">
            <ScrollArea className="flex-1 p-2">
              {!manifest && !loading && (
                <div className="text-sm text-muted-foreground p-4 text-center">暂无文件索引</div>
              )}
              {manifest && Object.keys(manifest.files || {}).length === 0 && (
                <div className="text-sm text-muted-foreground p-4 text-center">空文件夹</div>
              )}
              {manifest && manifest.files && (
                <div className="space-y-1">
                  {Object.entries(manifest.files).map(([key, value]) => {
                    if (typeof value === "string") {
                      return (
                        <Button 
                          key={key} 
                          variant={selectedFile === key ? "secondary" : "ghost"} 
                          className="w-full justify-start text-xs font-normal px-2 h-8"
                          onClick={() => handleSelectFile(key)}
                        >
                          <FileText className="w-3.5 h-3.5 mr-2 shrink-0 text-muted-foreground" />
                          <span className="truncate">{key}</span>
                        </Button>
                      )
                    } else if (typeof value === "object" && value !== null) {
                      return (
                        <div key={key} className="pt-2 pb-1">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2 mb-1">
                            {key}
                          </div>
                          {Object.keys(value).map(subKey => {
                            const fullKey = `${key}/${subKey}`
                            return (
                              <Button 
                                key={fullKey} 
                                variant={selectedFile === fullKey ? "secondary" : "ghost"} 
                                className="w-full justify-start text-xs font-normal px-2 h-8 pl-4"
                                onClick={() => handleSelectFile(fullKey)}
                              >
                                <FileText className="w-3.5 h-3.5 mr-2 shrink-0 text-muted-foreground" />
                                <span className="truncate">{subKey}</span>
                              </Button>
                            )
                          })}
                        </div>
                      )
                    }
                    return null
                  })}
                </div>
              )}
            </ScrollArea>
          </div>

          {/* Content area */}
          <div className="flex-1 flex flex-col bg-background overflow-hidden relative">
            {selectedFile ? (
              <>
                <div className="h-10 border-b border-border/40 px-4 flex items-center text-sm font-medium text-muted-foreground bg-muted/5">
                  {selectedFile}
                </div>
                <ScrollArea className="flex-1 p-6">
                  {contentLoading ? (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      <RefreshCw className="w-5 h-5 animate-spin mr-2" /> 读取中...
                    </div>
                  ) : (
                    <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                      {fileContent}
                    </pre>
                  )}
                </ScrollArea>
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                <ChevronRight className="w-4 h-4 mr-1" />
                在左侧选择要查看的文件
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
