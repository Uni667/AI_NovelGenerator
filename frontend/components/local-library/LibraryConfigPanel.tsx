import { useState } from "react"
import { Settings, FolderOpen, ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import type { LocalLibraryConfig } from "@/lib/types"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

interface LibraryConfigPanelProps {
  config: LocalLibraryConfig | null
  onConfigUpdated: () => void
}

export function LibraryConfigPanel({ config, onConfigUpdated }: LibraryConfigPanelProps) {
  const [sourceDir, setSourceDir] = useState(config?.source_dir || "")
  const [essenceDir, setEssenceDir] = useState(config?.essence_dir || "")
  const [allowAccess, setAllowAccess] = useState(config?.allow_local_file_access || false)
  const [watcherEnabled, setWatcherEnabled] = useState(config?.watcher_enabled || false)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.localLibrary.updateConfig({
        source_dir: sourceDir,
        essence_dir: essenceDir,
        allow_local_file_access: allowAccess,
        watcher_enabled: watcherEnabled,
      })
      toast.success("配置已保存")
      onConfigUpdated()
    } catch (e: any) {
      toast.error(e?.message || "保存配置失败")
    } finally {
      setSaving(false)
    }
  }

  const handleTestAccess = async () => {
    try {
      const res = await api.localLibrary.testConfig({ source_dir: sourceDir, essence_dir: essenceDir, allow_local_file_access: allowAccess })
      if (res.success) {
        toast.success("权限测试通过！")
      } else {
        toast.error(`测试失败: ${(res as any).error || "未知错误"}`)
      }
    } catch (e: any) {
      toast.error(e?.message || "权限测试失败")
    }
  }

  return (
    <Card className="glass-panel border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <CardTitle className="text-base flex items-center gap-2">
          <Settings className="w-4 h-4 text-muted-foreground" /> 本地库配置 Contract
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">小说原文文件夹 (source_dir)</Label>
          <div className="flex gap-2">
            <Input
              value={sourceDir}
              onChange={(e) => setSourceDir(e.target.value)}
              placeholder="例如: D:\NovelLibrary\books"
              className="bg-background/50 h-10 border-border/60"
            />
            <Button variant="outline" size="icon" className="h-10 w-10 shrink-0">
              <FolderOpen className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">精华输出文件夹 (essence_dir)</Label>
          <div className="flex gap-2">
            <Input
              value={essenceDir}
              onChange={(e) => setEssenceDir(e.target.value)}
              placeholder="例如: D:\NovelLibrary\essences"
              className="bg-background/50 h-10 border-border/60"
            />
            <Button variant="outline" size="icon" className="h-10 w-10 shrink-0">
              <FolderOpen className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 pt-2">
          <div className="flex items-center space-x-2 bg-background/30 p-3 rounded-lg border border-border/50 flex-1">
            <Switch
              id="allow-access"
              checked={allowAccess}
              onCheckedChange={setAllowAccess}
            />
            <Label htmlFor="allow-access" className="text-sm font-medium cursor-pointer">
              允许本地读写
              <span className="block text-xs text-muted-foreground mt-0.5">必须开启以读取原文件并写入精华</span>
            </Label>
          </div>
          
          <div className="flex items-center space-x-2 bg-background/30 p-3 rounded-lg border border-border/50 flex-1">
            <Switch
              id="watcher-enabled"
              checked={watcherEnabled}
              onCheckedChange={setWatcherEnabled}
            />
            <Label htmlFor="watcher-enabled" className="text-sm font-medium cursor-pointer">
              自动监控 (Watcher)
              <span className="block text-xs text-muted-foreground mt-0.5">当检测到新 txt 时自动开始吸收</span>
            </Label>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 mt-2 border-t border-border/30">
          <Button variant="outline" onClick={handleTestAccess}>
            <ShieldCheck className="w-4 h-4 mr-2" />
            测试读写权限
          </Button>
          <Button onClick={handleSave} disabled={saving} className="shadow-glow">
            {saving ? "保存中..." : "保存配置"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
