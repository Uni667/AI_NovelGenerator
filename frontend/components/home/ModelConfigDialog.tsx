"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { RefreshCw, KeyRound, Wifi, ShieldCheck } from "lucide-react"

interface ModelConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

const PROVIDERS = [
  { value: "siliconflow", label: "硅基流动 (SiliconFlow)" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "openai", label: "OpenAI" },
  { value: "qwen", label: "通义千问 (Qwen)" },
  { value: "anthropic", label: "Claude" },
]

export function ModelConfigDialog({ open, onOpenChange, onSuccess }: ModelConfigDialogProps) {
  const [provider, setProvider] = useState("siliconflow")
  const [apiKey, setApiKey] = useState("")
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)

  const handleTest = async () => {
    if (!apiKey.trim()) {
      toast.error("请先输入 API Key")
      return
    }
    setTesting(true)
    try {
      const result = await api.config.modelQuickSetup({ provider, api_key: apiKey.trim() })
      if (result.success) {
        toast.success(`🎉 连接测试成功！底层节点已就绪：${result.data.chatModel}`)
      } else {
        toast.error("连接测试失败，请检查 API Key 和服务商")
      }
    } catch (err: any) {
      toast.error(err?.message || "连接测试失败，请检查网络或密钥")
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) {
      toast.error("请先输入 API Key")
      return
    }
    setSaving(true)
    try {
      const result = await api.config.modelQuickSetup({ provider, api_key: apiKey.trim() })
      if (result.success) {
        toast.success("✨ 全局大模型节点配置已挂载成功！")
        onOpenChange(false)
        setApiKey("") 
        if (onSuccess) onSuccess()
      } else {
        toast.error("配置挂载失败，请检查 API Key 和服务商")
      }
    } catch (err: any) {
      toast.error(err?.message || "配置保存失败，请稍后重试")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm bg-background/95 backdrop-blur-xl border-border/60 p-6 rounded-2xl">
        <form onSubmit={handleSave} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-foreground flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-primary" />
              配置全局模型节点
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              配置底层算力引擎，小说大纲生成和正文创作都需要 API 密钥连接。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">云端服务商 (Provider)</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full bg-[#0A0915] border border-border/60 rounded-lg px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary/50 h-9"
              >
                {PROVIDERS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">授权令牌 (API Key)</label>
              <Input
                autoComplete="off"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="bg-black/20 border-border/60 focus:border-primary/50 text-xs h-9 font-mono rounded-lg"
                required
              />
            </div>
            
            <div className="bg-primary/5 border border-primary/10 rounded-lg p-3 text-[11px] text-muted-foreground leading-relaxed">
              <span className="font-bold text-primary block mb-0.5">💡 推荐使用 DeepSeek / 硅基流动：</span>
              硅基流动（SiliconFlow）提供了超低价格的 DeepSeek 文本生成服务，且生成速度极快。
            </div>
          </div>

          <DialogFooter className="pt-2 flex gap-2 justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs rounded-lg px-4 flex items-center gap-1.5"
              onClick={handleTest}
              disabled={testing || saving}
            >
              {testing ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Wifi className="h-3.5 w-3.5" />}
              {testing ? "测试中..." : "测试连接"}
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-9 text-xs rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white border-none font-semibold px-4 flex items-center gap-1.5"
              disabled={testing || saving}
            >
              {saving ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
              {saving ? "保存中..." : "确认保存"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
