"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Upload, Trash2, RefreshCw, Loader2, BookMarked } from "lucide-react"
import { useProjectContext } from "./ProjectContext"
import { useState, useCallback, useEffect } from "react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"

export function KnowledgeTab() {
  const { projectId } = useProjectContext()

  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null)
  const [knowledgeFiles, setKnowledgeFiles] = useState<any[]>([])
  const [knowledgeLoading, setKnowledgeLoading] = useState(false)
  const [knowledgeError, setKnowledgeError] = useState("")
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [knowledgeDeleteTarget, setKnowledgeDeleteTarget] = useState<any>(null)

  const refreshKnowledgeFiles = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await api.knowledge.list(projectId)
      setKnowledgeFiles(res || [])
      setKnowledgeError("")
    } catch (e: any) {
      setKnowledgeError(e.message || "加载知识库失败")
      setKnowledgeFiles([])
    }
  }, [projectId])

  useEffect(() => {
    refreshKnowledgeFiles()
  }, [refreshKnowledgeFiles])

  const handleUploadKnowledge = async () => {
    if (!knowledgeFile) return
    setKnowledgeLoading(true)
    try {
      const result = await api.knowledge.upload(projectId, knowledgeFile)
      toast.success(result.message || "上传成功")
      setKnowledgeFile(null)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "知识库上传失败")
    } finally {
      setKnowledgeLoading(false)
    }
  }

  const handleClearVector = async () => {
    try {
      await api.knowledge.clearVector(projectId)
      toast.success("向量库已清空")
      setClearDialogOpen(false)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "清空向量库失败")
    }
  }

  const handleDeleteKnowledgeFile = async (file: any) => {
    try {
      await api.knowledge.delete(projectId, file.id)
      toast.success(`已删除 ${file.filename}`)
      setKnowledgeDeleteTarget(null)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "删除失败")
    }
  }

  const handleReimportKnowledgeFile = async (file: any) => {
    try {
      await api.knowledge.reimport(projectId, file.id)
      toast.success(`正在重建 ${file.filename} 索引`)
      await refreshKnowledgeFiles()
    } catch (error: any) {
      toast.error(error?.message || "重建索引失败")
    }
  }

  const formatFileSize = (size?: number) => {
    if (!size || size <= 0) return "0 B"
    const units = ["B", "KB", "MB", "GB"]
    let value = size
    let unitIndex = 0
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024
      unitIndex += 1
    }
    return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
  }

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-border/40">
        <CardHeader>
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <BookMarked className="h-5 w-5 text-primary" />知识库配置
          </CardTitle>
          <CardDescription>上传设定集、世界观、人物细纲等 TXT 设定文档，AI 写作时将自动检索参考内容。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <Input
              type="file"
              accept=".txt,.md"
              onChange={e => setKnowledgeFile(e.target.files?.[0] || null)}
              className="flex-1 bg-background/50 rounded-xl"
            />
            <Button
              onClick={handleUploadKnowledge}
              disabled={!knowledgeFile || knowledgeLoading}
              className="rounded-xl shadow-md"
            >
              {knowledgeLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              上传并同步
            </Button>
          </div>
          <Separator className="bg-border/30" />
          <div className="flex items-center justify-between flex-wrap gap-3">
            <Button
              variant="destructive"
              onClick={() => setClearDialogOpen(true)}
              disabled={knowledgeLoading}
              className="rounded-xl text-xs h-9 px-3.5"
            >
              <Trash2 className="h-4 w-4 mr-1.5" />清空向量数据库
            </Button>
            <span className="text-[11px] text-muted-foreground">
              提示: 清空操作仅清除已向量化的索引，可在列表内重试导入单个文件。
            </span>
          </div>

          {knowledgeError && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-3.5 text-xs text-destructive">
              {knowledgeError}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="glass-panel border-border/40">
        <CardHeader>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <CardTitle className="text-base font-bold">知识库文件列表</CardTitle>
              <CardDescription className="text-xs">支持重导入索引或彻底删除文件</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void refreshKnowledgeFiles()}
              disabled={knowledgeLoading}
              className="bg-card/40 border-border/80 text-xs"
            >
              {knowledgeLoading ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
              刷新列表
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-2">
          {knowledgeLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full rounded-xl" />
              <Skeleton className="h-16 w-full rounded-xl" />
            </div>
          ) : knowledgeFiles.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/60 py-10 text-center text-xs text-muted-foreground bg-card/10">
              <BookMarked className="h-8 w-8 mx-auto mb-2 opacity-30 text-primary" />
              暂无已上传的知识参考文档
            </div>
          ) : (
            <div className="space-y-3">
              {knowledgeFiles.map((file: any) => (
                <div
                  key={file.id}
                  className="rounded-xl border border-border/50 bg-card/20 p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-primary/15 transition-all duration-200"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="font-semibold text-sm truncate text-foreground/95">{file.filename}</p>
                    <p className="text-[10px] text-muted-foreground flex items-center gap-1.5 flex-wrap">
                      <span>文件大小: {formatFileSize(file.file_size)}</span>
                      <span>•</span>
                      <span>{file.imported ? "向量数据库就绪" : "等待导入"}</span>
                      {file.created_at && (
                        <>
                          <span>•</span>
                          <span>上传时间: {file.created_at.slice(0, 19).replace("T", " ")}</span>
                        </>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 flex-wrap">
                    <Badge
                      variant={file.imported ? "default" : "outline"}
                      className={
                        file.imported
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-secondary text-muted-foreground border-border"
                      }
                    >
                      {file.imported ? "已索引" : "未索引"}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReimportKnowledgeFile(file)}
                      disabled={knowledgeLoading}
                      className="bg-card/30 border-border/70 text-xs h-8 px-2.5"
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                      重新构建
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setKnowledgeDeleteTarget(file)}
                      disabled={knowledgeLoading}
                      className="text-xs h-8 px-2.5"
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      删除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Clear Knowledge Base Dialog */}
      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent className="glass-panel border-border/45 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">确认清空向量库</DialogTitle>
            <DialogDescription className="text-sm mt-1">
              此操作将永久删除所有已导入的知识库向量数据，不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 gap-2">
            <Button variant="outline" onClick={() => setClearDialogOpen(false)} className="hover:bg-accent/40">取消</Button>
            <Button variant="destructive" onClick={handleClearVector}>确认清空</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Knowledge File Dialog */}
      <Dialog open={!!knowledgeDeleteTarget} onOpenChange={(open) => { if (!open) setKnowledgeDeleteTarget(null) }}>
        <DialogContent className="glass-panel border-border/45 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">确认删除知识文件</DialogTitle>
            <DialogDescription className="text-sm mt-1">
              将删除 <span className="font-semibold text-foreground">{knowledgeDeleteTarget?.filename || "该文件"}</span>，并同步重建知识库向量。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 gap-2">
            <Button variant="outline" onClick={() => setKnowledgeDeleteTarget(null)} className="hover:bg-accent/40">取消</Button>
            <Button variant="destructive" onClick={() => knowledgeDeleteTarget && handleDeleteKnowledgeFile(knowledgeDeleteTarget)}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
