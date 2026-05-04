"use client"

import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FileText, Upload } from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api-client"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  onImportSuccess: () => void
}

export function FileImportDialog({
  open,
  onOpenChange,
  projectId,
  onImportSuccess,
}: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [fileType, setFileType] = useState<string>("architecture")
  const [setCurrent, setSetCurrent] = useState(true)
  const [importing, setImporting] = useState(false)
  const [preview, setPreview] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    const ext = f.name.split(".").pop()?.toLowerCase()
    if (!ext || !["txt", "md", "json"].includes(ext)) {
      toast.error("仅支持 .txt、.md、.json 文件")
      return
    }
    setFile(f)
    const reader = new FileReader()
    reader.onload = () => setPreview((reader.result as string).slice(0, 2000))
    reader.readAsText(f)
  }

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    try {
      await api.projectFiles.import(projectId, file, fileType, setCurrent)
      toast.success(
        `${fileType === "architecture" ? "架构" : "章节目录"}导入成功`
      )
      onImportSuccess()
      onOpenChange(false)
      setFile(null)
      setPreview("")
    } catch (err: any) {
      toast.error(err.message || "导入失败")
    } finally {
      setImporting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>导入文件</DialogTitle>
          <DialogDescription>
            导入小说架构或章节目录文件。支持 .txt、.md、.json 格式。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label>导入类型</Label>
            <Select value={fileType} onValueChange={(v) => v && setFileType(v)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="architecture">小说架构</SelectItem>
                <SelectItem value="outline">章节目录</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div
            className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            {file ? (
              <div className="space-y-1">
                <FileText className="h-8 w-8 mx-auto text-primary" />
                <p className="font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {fileType === "architecture" ? "架构文件" : "目录文件"} ·
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  点击选择文件或拖拽到此处
                </p>
              </div>
            )}
            <input
              type="file"
              ref={fileRef}
              className="hidden"
              accept=".txt,.md,.json"
              onChange={handleFileChange}
            />
          </div>

          {preview && (
            <div>
              <Label>内容预览</Label>
              <ScrollArea className="h-40 rounded border p-3">
                <pre className="text-xs whitespace-pre-wrap">{preview}</pre>
              </ScrollArea>
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={setCurrent}
              onChange={(e) => setSetCurrent(e.target.checked)}
              id="set-current"
              className="h-4 w-4 rounded border-gray-300"
            />
            <Label htmlFor="set-current">
              导入后设为当前
              {fileType === "architecture" ? "架构" : "目录"}
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleImport} disabled={!file || importing}>
            {importing ? "导入中..." : "确认导入"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
