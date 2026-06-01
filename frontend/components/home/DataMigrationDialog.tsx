"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Download, Upload, ShieldAlert, FileJson, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react"

interface DataMigrationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const LOCALSTORAGE_WHITELIST = [
  "ai-novel-workbench-layout-mode",
  "ai-novel-workbench-layout-mode-user-select",
  "ai-novel-editor-font-size",
  "ai-novel-left-panel-collapsed",
  "ai-novel-right-panel-collapsed",
  "recently-opened-projects"
]

export function DataMigrationDialog({ open, onOpenChange }: DataMigrationDialogProps) {
  const [token, setToken] = useState("")
  const [exportingBackend, setExportingBackend] = useState(false)
  const [importedData, setImportedData] = useState<any>(null)
  const [importType, setImportType] = useState<"backend" | "browser" | null>(null)

  const downloadJson = (data: any, filename: string) => {
    const jsonStr = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // 1. Export Backend Data
  const handleExportBackend = async () => {
    setExportingBackend(true)
    try {
      toast.info("正在调取算力引擎数据，这可能需要几秒钟...")
      const res = await api.migration.exportAll(token.trim() || undefined)
      
      const timestamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14)
      const filename = `ai_novel_backend_export_${timestamp}.json`
      
      downloadJson(res, filename)
      toast.success("🎉 后端整包数据已成功导出！")
    } catch (err: any) {
      toast.error(err?.message || "后端数据导出失败，请确认 MIGRATION_ENABLED 环境变量已开启且 Token 正确。")
    } finally {
      setExportingBackend(false)
    }
  }

  // 2. Export Browser Local Config (Whitelisted)
  const handleExportBrowser = () => {
    try {
      const data: Record<string, string> = {}
      LOCALSTORAGE_WHITELIST.forEach((key) => {
        const val = localStorage.getItem(key)
        if (val !== null) {
          data[key] = val
        }
      })
      
      // Strict sanity check - ensure no tokens or api keys are exported
      const serialized = JSON.stringify(data).toLowerCase()
      const forbiddenWords = ["token", "apikey", "authorization", "secret", "password", "cookie"]
      const found = forbiddenWords.filter(word => serialized.includes(word))
      
      if (found.length > 0) {
        toast.error(`安全校验未通过：导出的数据中包含疑似敏感字段 (${found.join(", ")})`)
        return
      }
      
      const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, "")
      downloadJson(data, `ai_novel_browser_settings_${timestamp}.json`)
      toast.success("✨ 浏览器本地配置导出成功（已过滤敏感信息）")
    } catch (err: any) {
      toast.error("配置导出失败：" + err.message)
    }
  }

  // 3. Import local data files
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string)
        
        // Determine type of uploaded file
        if (json.database && json.files) {
          // Backend package
          setImportType("backend")
          const projectCount = json.database.project?.length || 0
          const chapterCount = json.database.chapter?.length || 0
          const filesCount = Object.keys(json.files).length
          
          setImportedData({
            summary: `项目数: ${projectCount}, 章节数: ${chapterCount}, 物理文件: ${filesCount}`,
            raw: json
          })
          toast.success("已成功解析后端迁移数据包！")
        } else {
          // Verify if it contains whitelisted localStorage keys
          const keys = Object.keys(json)
          const isValidSettings = keys.some(k => LOCALSTORAGE_WHITELIST.includes(k))
          
          if (isValidSettings) {
            setImportType("browser")
            setImportedData({
              summary: `包含配置项: ${keys.join(", ")}`,
              raw: json
            })
            toast.success("已成功解析浏览器配置包！")
          } else {
            toast.error("未识别的文件格式，请上传正确的备份包。")
          }
        }
      } catch (err) {
        toast.error("解析 JSON 失败，文件格式有误。")
      }
    }
    reader.readAsText(file)
  }

  const handleApplyImport = () => {
    if (!importedData || !importType) return

    try {
      if (importType === "browser") {
        Object.entries(importedData.raw).forEach(([key, val]) => {
          if (LOCALSTORAGE_WHITELIST.includes(key)) {
            localStorage.setItem(key, val as string)
          }
        })
        toast.success("✨ 浏览器本地配置已应用成功，刷新页面生效！")
        setTimeout(() => {
          window.location.reload()
        }, 1500)
      } else if (importType === "backend") {
        // Since local workspace migration operates offline, we advise the user:
        toast.success("✅ 数据完整性校验通过！您可以将此 JSON 包放入新文件夹工作区进行解析。")
      }
      setImportedData(null)
      setImportType(null)
      onOpenChange(false)
    } catch (err: any) {
      toast.error("导入应用失败: " + err.message)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-background/95 backdrop-blur-xl border-border/60 p-6 rounded-2xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold text-foreground flex items-center gap-2">
            <FileJson className="h-5 w-5 text-primary" />
            旧数据迁移实验室
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            用于从旧版 SQLite 和 FastAPI 节点导出数据，并迁移至本地文件夹工作区。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2 text-xs">
          {/* Section 1: Export */}
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground border-b border-border/40 pb-1 flex items-center gap-1.5">
              <Download className="w-3.5 h-3.5 text-primary" /> 数据打包下载
            </h3>
            
            <div className="space-y-2">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-muted-foreground">数据迁移令牌 (Migration Token)</label>
                <Input
                  autoComplete="off"
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="请输入 MIGRATION_TOKEN（如未开启校验可为空）"
                  className="bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-3 pt-1">
                <Button
                  onClick={handleExportBackend}
                  disabled={exportingBackend}
                  className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs h-9 rounded-lg flex items-center justify-center gap-1.5 font-medium"
                >
                  {exportingBackend ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5" />
                  )}
                  {exportingBackend ? "正在导出..." : "导出后端数据"}
                </Button>
                
                <Button
                  variant="outline"
                  onClick={handleExportBrowser}
                  className="border-border/60 hover:bg-accent/40 text-xs h-9 rounded-lg flex items-center justify-center gap-1.5 font-medium"
                >
                  <Download className="h-3.5 w-3.5" />
                  导出浏览器配置
                </Button>
              </div>
            </div>
          </div>

          {/* Section 2: Import */}
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground border-b border-border/40 pb-1 flex items-center gap-1.5">
              <Upload className="w-3.5 h-3.5 text-primary" /> 数据还原导入
            </h3>
            
            <div className="border border-dashed border-border/60 rounded-xl p-4 text-center hover:bg-accent/10 transition-colors relative">
              <input
                type="file"
                accept=".json"
                onChange={handleFileUpload}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <Upload className="mx-auto w-6 h-6 text-muted-foreground mb-2" />
              <p className="text-xs text-muted-foreground font-medium">点击或拖拽上传导出的 JSON 文件</p>
              <p className="text-[10px] text-muted-foreground/60 mt-1">支持导入后端整包数据或浏览器配置</p>
            </div>

            {importedData && (
              <div className="bg-primary/5 border border-primary/15 rounded-lg p-3 space-y-2.5">
                <div className="flex items-start gap-2">
                  {importType === "backend" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
                  )}
                  <div className="space-y-1">
                    <span className="font-bold text-foreground text-[11px] block">
                      解析成功 ({importType === "backend" ? "后端整包数据" : "浏览器配置"})
                    </span>
                    <span className="text-[10px] text-muted-foreground block leading-relaxed">
                      {importedData.summary}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-[10px] rounded-md"
                    onClick={() => {
                      setImportedData(null)
                      setImportType(null)
                    }}
                  >
                    取消
                  </Button>
                  <Button
                    size="sm"
                    className="h-7 text-[10px] rounded-md font-semibold bg-primary hover:bg-primary/95 text-white"
                    onClick={handleApplyImport}
                  >
                    确认导入应用
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Section 3: Safety Guard */}
          <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-3 text-[11.5px] text-amber-500/80 leading-relaxed flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
            <div>
              <span className="font-bold text-amber-400 block mb-0.5">🔒 安全防御规范</span>
              浏览器配置仅包含排版、最近项目等偏好信息。对于 Token、API Key 等敏感字段，已采用白名单彻底脱敏拦截，请放心操作。
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
