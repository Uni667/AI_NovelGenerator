import { useState } from "react"
import { Search, Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { api } from "@/lib/api-client"

interface LibraryScanPanelProps {
  onScanComplete: () => void
  disabled: boolean
}

export function LibraryScanPanel({ onScanComplete, disabled }: LibraryScanPanelProps) {
  const [scanning, setScanning] = useState(false)
  const [lastReport, setLastReport] = useState<{new_books: number, changed_books: number} | null>(null)

  const handleScan = async () => {
    setScanning(true)
    try {
      const report = await api.localLibrary.scan()
      setLastReport(report)
      toast.success(`扫描完成！新增书: ${report.new_books}, 修改: ${report.changed_books}`)
      onScanComplete()
    } catch (e: any) {
      toast.error(e?.message || "扫描失败")
    } finally {
      setScanning(false)
    }
  }

  return (
    <Card className="glass-panel border-border/40 h-full flex flex-col">
      <CardHeader className="pb-3 border-b border-border/30">
        <CardTitle className="text-base flex items-center gap-2">
          <Search className="w-4 h-4 text-muted-foreground" /> 库目录扫描
        </CardTitle>
        <CardDescription className="text-xs">
          扫描 source_dir 中的 txt 文件并同步到数据库
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-6 flex-1 flex flex-col items-center justify-center space-y-4">
        <Button 
          size="lg" 
          onClick={handleScan} 
          disabled={disabled || scanning}
          className="w-full max-w-[200px] h-14 rounded-xl text-md shadow-glow transition-all active:scale-95"
        >
          {scanning ? (
            <div className="flex items-center">
              <span className="w-5 h-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
              正在扫描目录...
            </div>
          ) : (
            <div className="flex items-center">
              <Search className="w-5 h-5 mr-2" />
              立即执行全量扫描
            </div>
          )}
        </Button>
        
        {disabled && (
          <p className="text-xs text-amber-500/80 flex items-center gap-1.5 mt-2 bg-amber-500/10 px-3 py-1.5 rounded-md">
            <Info className="w-3 h-3" />
            请先配置原文文件夹并开启读取权限
          </p>
        )}
        
        {lastReport && !scanning && (
          <div className="text-xs text-muted-foreground bg-secondary/30 px-4 py-2 rounded-lg mt-2">
            上次扫描结果: <span className="font-semibold text-foreground">新增 {lastReport.new_books} 本</span>, 
            <span className="font-semibold text-foreground ml-1">更新 {lastReport.changed_books} 本</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
