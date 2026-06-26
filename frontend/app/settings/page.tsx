"use client"

import { useCallback, useEffect, useState, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  KeyRound,
  Plus,
  Pencil,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Wifi,
  Database,
  Cpu,
  Fingerprint,
  ArrowLeft
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { ApiCredential, ModelProfile } from "@/lib/types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog"

const PROVIDERS = [
  { value: "siliconflow", label: "硅基流动" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "openai", label: "OpenAI" },
  { value: "qwen", label: "通义千问" },
  { value: "anthropic", label: "Claude" },
]

const PROVIDER_DISPLAY: Record<string, string> = {
  siliconflow: "硅基流动",
  deepseek: "DeepSeek",
  openai: "OpenAI",
  qwen: "通义千问",
  anthropic: "Claude",
  custom: "自定义",
  local: "本地",
}

const PURPOSE_LABELS: Record<string, string> = {
  general: "通用",
  architecture: "架构",
  outline: "大纲",
  draft: "草稿",
  review: "审校",
  summary: "摘要",
  polish: "润色",
  feedback: "反馈",
  worldbuilding: "世界观",
  character: "角色",
  embedding: "向量",
  rerank: "重排",
}

interface EnvConfig {
  provider: string
  providerLabel: string
  model: string
  baseUrl: string
  interface: string
  apiKeyMasked: string
  isEnvFallback: boolean
}

interface ModelStatus {
  state?: "empty" | "invalid" | "ready"
  title?: string
  description?: string
  chatReady: boolean
  coreReady: boolean
  embeddingReady: boolean
  embeddingMessage?: string
  provider?: string
  providerLabel?: string
  chatProvider?: string
  chatModel?: string
  lastTestedAt?: string
  recentTestedAt?: string
  chatErrors?: string[]
  activeCredentials?: number
  hasCredential?: boolean
  hasChatProfile?: boolean
  message?: string
  envConfig?: EnvConfig | null
}

interface InvocationLog {
  id: string
  created_at: string
  success: boolean
  provider: string
  model: string
  purpose: string
  latency_ms?: number
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback
}

function errorCode(error: unknown) {
  return typeof error === "object" && error ? (error as { code?: string }).code : undefined
}

function errorCount(error: unknown) {
  if (!error || typeof error !== "object") return undefined
  const count = (error as { details?: { count?: unknown } }).details?.count
  return typeof count === "number" ? count : undefined
}

function formatTime(value?: string) {
  if (!value) return "暂未记录"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("zh-CN", { hour12: false })
}

function providerLabel(provider?: string) {
  return PROVIDER_DISPLAY[provider || ""] || provider || "未识别"
}

export default function SettingsPage() {
  const router = useRouter()
  const [status, setStatus] = useState<ModelStatus | null>(null)
  const [credentials, setCredentials] = useState<ApiCredential[]>([])
  const [profiles, setProfiles] = useState<ModelProfile[]>([])
  const [logs, setLogs] = useState<InvocationLog[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showKeyForm, setShowKeyForm] = useState(false)
  const [working, setWorking] = useState("")

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [nextStatus, nextCredentials, nextProfiles, nextLogs] = await Promise.all([
        api.config.modelStatus().catch(() => null),
        api.config.listCredentials().catch(() => []),
        api.config.listProfiles().catch(() => []),
        api.config.listInvocationLogs(20).catch(() => []),
      ])
      setStatus(nextStatus)
      setCredentials(nextCredentials)
      setProfiles(nextProfiles)
      setLogs(nextLogs)
      setShowKeyForm(!(nextStatus as ModelStatus | null)?.chatReady && (nextStatus as ModelStatus | null)?.state !== "invalid")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const handleReset = async () => {
    if (!confirm("这只会清空模型服务账号和模型配置，不会删除小说项目和章节，确定继续吗？")) return
    setWorking("reset")
    try {
      const result = await api.config.modelReset()
      toast.success(result.message)
      setShowAdvanced(false)
      setShowKeyForm(true)
      await loadAll()
    } catch (error) {
      toast.error(errorMessage(error, "清空失败，请稍后重试。"))
    } finally {
      setWorking("")
    }
  }

  const handleRepair = async () => {
    setWorking("repair")
    try {
      const result = await api.config.modelRepair()
      toast.success(result.message || "修复完成。")
      await loadAll()
    } catch (error) {
      toast.error(errorMessage(error, "修复失败，请稍后重试。"))
    } finally {
      setWorking("")
    }
  }

  const handleRetest = async () => {
    const chatProfile = profiles.find((item) => item.type === "chat")
    const credential = credentials[0]
    if (!chatProfile && !credential) {
      toast.error("你还没有配置文本生成模型，请先完成模型设置。")
      setShowKeyForm(true)
      return
    }
    setWorking("test")
    try {
      if (chatProfile) {
        const result = await api.config.testProfile(chatProfile.id)
        toast.success(result.message || "测试成功")
      } else if (credential) {
        const result = await api.config.testCredential(credential.id)
        toast.success(result.message || "测试成功")
      }
      await loadAll()
    } catch (error) {
      toast.error(errorMessage(error, "测试失败，请检查 API Key 和服务商是否匹配。"))
    } finally {
      setWorking("")
    }
  }

  const state = status?.chatReady ? "ready" : status?.state || (status?.hasCredential || status?.hasChatProfile ? "invalid" : "empty")

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 md:p-8 min-h-[calc(100vh-2rem)]">
      {/* Background ambient gradient to match projects */}
      <div className="absolute top-0 left-0 w-full h-[50vh] bg-gradient-to-b from-primary/5 via-primary/5 to-transparent pointer-events-none -z-10" />
      
      <div className="shrink-0">
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => router.push("/")}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          返回项目列表
        </Button>
      </div>

      <div className="flex items-center justify-between gap-3 bg-card/40 border border-border/50 p-6 rounded-2xl backdrop-blur-xl shadow-lg">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent flex items-center gap-3">
            <Database className="w-8 h-8 text-primary" /> 全局大模型节点管理
          </h1>
          <p className="text-sm text-muted-foreground mt-2 font-medium">配置底层算力节点引擎，为各个小说项目提供 AI 生成动力。</p>
        </div>
        <Button variant="outline" onClick={loadAll} disabled={loading} className="shadow-glow hover:text-primary">
          <RefreshCw className={`size-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          刷新节点状态
        </Button>
      </div>

      <div className="space-y-6">
        {loading ? (
          <Card className="glass-panel border-border/40">
            <CardContent className="p-12 flex flex-col items-center justify-center text-sm text-muted-foreground">
              <RefreshCw className="size-8 animate-spin mb-4 text-primary/50" />
              正在连接算力节点网络...
            </CardContent>
          </Card>
        ) : state === "ready" ? (
          <ReadyState
            status={status}
            working={working}
            showAdvanced={showAdvanced}
            onChangeKey={() => setShowKeyForm((value) => !value)}
            onRetest={handleRetest}
            onReset={handleReset}
            onToggleAdvanced={() => setShowAdvanced((value) => !value)}
          />
        ) : state === "invalid" ? (
          <InvalidState
            status={status}
            working={working}
            showAdvanced={showAdvanced}
            onRetest={handleRetest}
            onReset={handleReset}
            onRepair={handleRepair}
            onToggleAdvanced={() => setShowAdvanced((value) => !value)}
          />
        ) : (
          <EmptyState />
        )}

        {(state === "empty" || showKeyForm) && <QuickSetupCard onDone={loadAll} />}

        {/* 服务端环境变量兜底 API 提示 */}
        {status?.envConfig && <EnvConfigBanner envConfig={status.envConfig} />}

        {/* 统一的高级控制台折叠开关，始终可被触及 */}
        {(state === "empty" || showKeyForm) && (
          <div className="flex justify-center md:justify-end pr-2 pt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAdvanced((value) => !value)}
              className="text-muted-foreground hover:text-primary transition-colors text-xs font-semibold"
            >
              {showAdvanced ? "收起底层控制台" : "展开底层控制台"}
              <ChevronDown className={`size-3.5 ml-1 transition-transform duration-300 ${showAdvanced ? "rotate-180" : ""}`} />
            </Button>
          </div>
        )}

        {showAdvanced && (
          <AdvancedSettings
            credentials={credentials}
            profiles={profiles}
            logs={logs}
            onChanged={loadAll}
            onRepair={handleRepair}
          />
        )}
      </div>
    </main>
  )
}

function EmptyState() {
  return (
    <Card className="glass-panel border-border/40">
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Cpu className="text-muted-foreground" /> 节点空闲</CardTitle>
        <CardDescription>当前数据库中未配置算力节点。服务器可能已通过环境变量预置 API（见下方），可直接生成小说。</CardDescription>
      </CardHeader>
    </Card>
  )
}

function EnvConfigBanner({ envConfig }: { envConfig: EnvConfig }) {
  return (
    <Card className="glass-panel border-amber-500/30 bg-amber-500/5 relative overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="absolute top-0 left-0 w-1 h-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]" />
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-amber-400 text-base">
            <Cpu className="size-5" />
            服务端预置 API（当前实际生效）
          </CardTitle>
          <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30 text-xs">ENV_VAR</Badge>
        </div>
        <CardDescription className="text-amber-300/70 text-xs mt-1">
          以下配置来自服务器环境变量。您未在数据库配置时，系统自动使用此配置生成小说。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 font-mono text-sm">
          <div className="flex items-center justify-between bg-background/40 px-3 py-2 rounded border border-amber-500/20">
            <span className="text-muted-foreground text-xs">[PROVIDER_NODE]</span>
            <span className="text-amber-300 font-semibold">{envConfig.providerLabel || envConfig.provider}</span>
          </div>
          <div className="flex items-center justify-between bg-background/40 px-3 py-2 rounded border border-amber-500/20">
            <span className="text-muted-foreground text-xs">[ACTIVE_MODEL]</span>
            <span className="text-amber-300 font-semibold text-primary">{envConfig.model || "未设置"}</span>
          </div>
          <div className="flex items-center justify-between bg-background/40 px-3 py-2 rounded border border-amber-500/20">
            <span className="text-muted-foreground text-xs">[BASE_URL]</span>
            <span className="text-amber-300/80 text-xs truncate max-w-xs">{envConfig.baseUrl || "（使用默认地址）"}</span>
          </div>
          <div className="flex items-center justify-between bg-background/40 px-3 py-2 rounded border border-amber-500/20">
            <span className="text-muted-foreground text-xs">[API_KEY]</span>
            <span className="text-amber-300 font-semibold">{envConfig.apiKeyMasked}</span>
          </div>
        </div>
        <p className="mt-3 text-xs text-amber-300/60 leading-relaxed">
          💡 如需切换 API，在上方「极速挂载算力节点」中填入新的 Key 后保存，数据库配置将优先于环境变量生效。
        </p>
      </CardContent>
    </Card>
  )
}

function InvalidState({
  status,
  working,
  showAdvanced,
  onRetest,
  onReset,
  onRepair,
  onToggleAdvanced,
}: {
  status: ModelStatus | null
  working: string
  showAdvanced: boolean
  onRetest: () => void
  onReset: () => void
  onRepair: () => void
  onToggleAdvanced: () => void
}) {
  return (
    <Card className="glass-panel border-red-500/30 bg-red-500/5 relative overflow-hidden group">
      <div className="absolute top-0 left-0 w-1 h-full bg-red-500 animate-pulse" />
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-red-500">
          <AlertTriangle className="size-5" />
          算力节点连接异常
        </CardTitle>
        <CardDescription className="text-red-400/80">当前模型配置不完整或不可用，建议重新测试或清空后重配。</CardDescription>
        {status?.chatErrors?.[0] ? (
          <div className="mt-2 p-3 bg-red-500/10 border border-red-500/20 rounded font-mono text-xs text-red-400">
            {status.chatErrors[0]}
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={onRetest} disabled={working === "test"} className="border-red-500/30 hover:bg-red-500/10 text-red-400">
          {working === "test" ? <RefreshCw className="size-4 mr-2 animate-spin" /> : <ShieldCheck className="size-4 mr-2" />}
          重新握手测试
        </Button>
        <Button variant="outline" onClick={onReset} disabled={working === "reset"} className="border-red-500/30 hover:bg-red-500/10 text-red-400">
          <Trash2 className="size-4 mr-2" />
          清除损坏节点
        </Button>
        <Button variant="outline" onClick={onRepair} disabled={working === "repair"} className="border-red-500/30 hover:bg-red-500/10 text-red-400">
          {working === "repair" ? <RefreshCw className="size-4 mr-2 animate-spin" /> : <RefreshCw className="size-4 mr-2" />}
          尝试自动修复
        </Button>
        <Button variant="ghost" onClick={onToggleAdvanced} className="hover:text-foreground">
          {showAdvanced ? "收起节点底座配置" : "展开节点底座配置"}
          <ChevronDown className={`size-4 ml-1 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
        </Button>
      </CardContent>
    </Card>
  )
}

function ReadyState({
  status,
  working,
  showAdvanced,
  onChangeKey,
  onRetest,
  onReset,
  onToggleAdvanced,
}: {
  status: ModelStatus | null
  working: string
  showAdvanced: boolean
  onChangeKey: () => void
  onRetest: () => void
  onReset: () => void
  onToggleAdvanced: () => void
}) {
  const currentProvider = status?.providerLabel || providerLabel(status?.chatProvider || status?.provider)
  const lastTested = status?.lastTestedAt || status?.recentTestedAt

  return (
    <Card className="glass-panel border-primary/30 relative overflow-hidden group hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.15)] transition-all duration-500">
      <div className="absolute top-0 left-0 w-1 h-full bg-primary shadow-[0_0_10px_oklch(0.68_0.19_285/1)]" />
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-primary font-bold">
            <div className="relative">
              <div className="absolute inset-0 bg-primary rounded-full blur-md opacity-50 animate-pulse" />
              <CheckCircle className="size-6 relative z-10" />
            </div>
            主节点引擎已上线 (Online)
          </CardTitle>
          <Badge className="bg-primary/20 text-primary border-primary/30 py-1 px-3">Status: Healthy</Badge>
        </div>
        <CardDescription className="space-y-2 mt-4 text-muted-foreground/80 font-mono text-sm">
          <div className="flex items-center justify-between bg-background/40 p-2 rounded border border-border/50">
            <span>[PROVIDER_NODE]</span>
            <span className="text-foreground font-semibold">{currentProvider}</span>
          </div>
          <div className="flex items-center justify-between bg-background/40 p-2 rounded border border-border/50">
            <span>[ACTIVE_MODEL]</span>
            <span className="text-foreground font-semibold text-primary">{status?.chatModel || "未记录"}</span>
          </div>
          <div className="flex items-center justify-between bg-background/40 p-2 rounded border border-border/50">
            <span>[LAST_HANDSHAKE]</span>
            <span className="text-foreground font-semibold">{formatTime(lastTested)}</span>
          </div>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3 mt-2">
        <Button variant="outline" onClick={onChangeKey} className="shadow-glow border-primary/20 hover:bg-primary/10">
          <KeyRound className="size-4 mr-2 text-primary" />
          更换权限密钥
        </Button>
        <Button variant="outline" onClick={onRetest} disabled={working === "test"} className="shadow-glow border-primary/20 hover:bg-primary/10">
          {working === "test" ? <RefreshCw className="size-4 mr-2 animate-spin" /> : <ShieldCheck className="size-4 mr-2 text-primary" />}
          心跳测试
        </Button>
        <Button variant="outline" onClick={onReset} disabled={working === "reset"} className="border-border/50 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30">
          <Trash2 className="size-4 mr-2" />
          熔断并重置
        </Button>
        <Button variant="ghost" onClick={onToggleAdvanced} className="ml-auto">
          {showAdvanced ? "收起底层控制台" : "展开底层控制台"}
          <ChevronDown className={`size-4 ml-1 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
        </Button>
      </CardContent>
    </Card>
  )
}

function QuickSetupCard({ onDone }: { onDone: () => void }) {
  const [provider, setProvider] = useState("siliconflow")
  const [apiKey, setApiKey] = useState("")
  const [saving, setSaving] = useState(false)

  const quickSetup = async () => {
    if (!apiKey.trim()) {
      toast.error("请填写 API Key。")
      return
    }
    setSaving(true)
    try {
      const result = await api.config.modelQuickSetup({ provider, api_key: apiKey.trim() })
      toast.success(result.data.message)
      setApiKey("")
      onDone()
    } catch (error) {
      toast.error(errorMessage(error, "测试失败，请检查 API Key 和服务商是否匹配。"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="glass-panel border-border/40 shadow-xl overflow-hidden relative transition-all duration-500 hover:shadow-glow">
      <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
        <Fingerprint className="w-32 h-32 text-primary" />
      </div>
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center gap-2 text-foreground font-bold">
          <KeyRound className="text-primary w-5 h-5 animate-pulse" /> 极速挂载算力节点
        </CardTitle>
        <CardDescription className="text-muted-foreground mt-1">
          只需注入您的 API Key，系统将在后台自动完成凭证绑定、文本大模型映射及知识库向量化配置。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 relative z-10">
        <div className="grid gap-5 md:grid-cols-[220px_1fr_auto] items-end">
          <Field label="云端服务商 (Provider)">
            <Select value={provider} onValueChange={(value) => value && setProvider(value)}>
              <SelectTrigger className="shadow-sm border-border/60 focus:ring-primary/50 bg-background/50 h-10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="授权令牌 (API Key)">
            <Input
              autoComplete="off"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="sk-..."
              className="shadow-sm border-border/60 focus:ring-primary/50 font-mono bg-background/50 h-10"
            />
          </Field>
          <Button className="w-full md:w-auto shadow-glow h-10 px-6 bg-primary hover:bg-primary/95 text-primary-foreground font-semibold" onClick={quickSetup} disabled={saving}>
            {saving ? <RefreshCw className="size-4 mr-2 animate-spin" /> : <Wifi className="size-4 mr-2" />}
            {saving ? "节点连接中..." : "挂载并上线"}
          </Button>
        </div>

        <div className="pt-2 border-t border-border/30 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground/90 font-medium">
          <span className="text-primary/90 font-semibold">自动化管线配给:</span>
          <span className="flex items-center gap-1"><span className="text-emerald-400 font-bold">✓</span> 自动加密凭证</span>
          <span className="flex items-center gap-1"><span className="text-emerald-400 font-bold">✓</span> 映射小说章节草稿路由</span>
          <span className="flex items-center gap-1"><span className="text-emerald-400 font-bold">✓</span> 开启全局知识检索向量库</span>
        </div>

        <div className="bg-primary/5 border border-primary/10 rounded-lg p-3 text-xs text-muted-foreground leading-relaxed">
          <span className="font-bold text-primary block mb-0.5">💡 创作者贴士：</span>
          建议选择 <span className="font-semibold text-foreground">DeepSeek</span> (或选用硅基流动平台)，在保证极佳中文文风和角色逻辑的前提下，其 Token 价格仅为传统商用模型的数十分之一，更契合长篇小说的海量生成需求。
        </div>
      </CardContent>
    </Card>
  )
}

function AdvancedSettings({
  credentials,
  profiles,
  logs,
  onChanged,
  onRepair,
}: {
  credentials: ApiCredential[]
  profiles: ModelProfile[]
  logs: InvocationLog[]
  onChanged: () => void
  onRepair: () => void
}) {
  return (
    <div className="space-y-6 animate-in slide-in-from-top-4 fade-in duration-500">
      <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm text-primary flex items-center gap-3">
        <AlertTriangle className="w-5 h-5" />
        <div>
          <span className="font-bold">底层控制台已解锁。</span>
          <p className="opacity-80 mt-0.5">普通用户无需修改此处内容。请谨慎操作账号凭证与网络路由。</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="glass-panel border-border/40 hover:border-border/80 transition-colors">
          <CardHeader className="pb-3 border-b border-border/30">
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-muted-foreground" /> 身份凭证池 (Credentials)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <CredentialList credentials={credentials} onChanged={onChanged} />
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/40 hover:border-border/80 transition-colors">
          <CardHeader className="pb-3 border-b border-border/30">
            <CardTitle className="text-base flex items-center gap-2">
              <Cpu className="w-4 h-4 text-muted-foreground" /> 路由配置矩阵 (Profiles)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ProfileList profiles={profiles} credentials={credentials} onChanged={onChanged} />
          </CardContent>
        </Card>
      </div>

      <Card className="glass-panel border-border/40">
        <CardHeader className="pb-3 border-b border-border/30 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Database className="w-4 h-4 text-muted-foreground" /> 调用遥测日志 (Telemetry Logs)
            </CardTitle>
            <CardDescription className="mt-1">最近 20 条网络调用记录。</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onRepair} className="shadow-glow">
            <RefreshCw className="size-3 mr-2" />
            自动修复路由
          </Button>
        </CardHeader>
        <CardContent className="pt-4">
          {logs.length ? (
            <div className="space-y-2">
              {logs.map((log) => (
                <div key={log.id} className="grid gap-3 rounded-lg border border-border/50 bg-background/50 p-3 text-sm md:grid-cols-[160px_80px_1fr_80px] items-center hover:bg-background/80 transition-colors">
                  <span className="text-muted-foreground font-mono text-xs">{formatTime(log.created_at)}</span>
                  <Badge variant={log.success ? "default" : "destructive"} className={log.success ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border-none" : ""}>
                    {log.success ? "Success" : "Failed"}
                  </Badge>
                  <span className="font-medium text-foreground/80">{providerLabel(log.provider)} <span className="text-muted-foreground mx-1">/</span> <span className="text-primary/80">{log.model || "未记录"}</span> <span className="text-muted-foreground mx-1">/</span> {log.purpose || "general"}</span>
                  <span className="text-right font-mono text-xs text-muted-foreground">{log.success ? `${log.latency_ms || 0}ms` : "---"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground border border-dashed border-border/50 rounded-lg">
              暂无遥测数据
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function CredentialList({ credentials, onChanged }: { credentials: ApiCredential[]; onChanged: () => void }) {
  const handleDelete = async (credential: ApiCredential) => {
    try {
      await api.config.deleteCredential(credential.id)
      toast.success("模型服务账号已删除。")
      onChanged()
    } catch (error) {
      if (errorCode(error) === "API_CREDENTIAL_IN_USE") {
        const count = errorCount(error)
        const target = typeof count === "number" && count > 0 ? `${count} 个模型配置` : "模型配置"
        if (confirm(`这个模型服务账号正在被 ${target} 使用，是否一并删除？`)) {
          try {
            await api.config.deleteCredential(credential.id, true)
            toast.success("模型服务账号和关联模型配置已删除。")
            onChanged()
          } catch (cascadeError) {
            toast.error(errorMessage(cascadeError, "删除失败，请稍后重试。"))
          }
        }
        return
      }
      toast.error(errorMessage(error, "删除失败，请稍后重试。"))
    }
  }

  if (!credentials.length) return <div className="py-6 text-center text-sm text-muted-foreground">暂无凭证数据</div>

  return (
    <div className="space-y-3">
      {credentials.map((credential) => (
        <div key={credential.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/50 bg-background/50 p-3 text-sm hover:bg-background/80 transition-colors">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className="font-bold text-foreground">{credential.name}</span>
              <Badge variant="secondary" className="text-xs bg-muted/50">{providerLabel(credential.provider)}</Badge>
              {credential.api_key_last4 && <span className="font-mono text-xs text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded border border-border/30">...{credential.api_key_last4}</span>}
            </div>
            <div className="flex items-center">
              <Badge variant={credential.status === "active" ? "default" : credential.status === "invalid" ? "destructive" : "outline"} className={credential.status === "active" ? "bg-emerald-500/20 text-emerald-400 border-none px-2 h-5" : "px-2 h-5"}>
                {credential.status === "active" ? "Active" : credential.status === "invalid" ? "Error" : "Untested"}
              </Badge>
            </div>
          </div>
          <div className="flex gap-1.5">
            <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-primary/20 hover:text-primary" title="重新测试" onClick={() =>
                api.config.testCredential(credential.id).then((result) => toast.success(result.message || "测试成功")).catch((error) => toast.error(errorMessage(error, "测试失败，请检查 API Key 和服务商是否匹配。"))).finally(onChanged)
              }>
              <Wifi className="size-4" />
            </Button>
            <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-destructive/20 hover:text-destructive" title="删除" onClick={() => handleDelete(credential)}>
              <Trash2 className="size-4" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}

function ProfileList({ profiles, credentials, onChanged }: { profiles: ModelProfile[]; credentials: ApiCredential[]; onChanged: () => void }) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<ModelProfile | null>(null)

  const handleCreate = () => {
    setEditingProfile(null)
    setDialogOpen(true)
  }

  const handleEdit = (profile: ModelProfile) => {
    setEditingProfile(profile)
    setDialogOpen(true)
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={handleCreate} disabled={!credentials.length}>
          <Plus className="size-3.5" />
          新建配置
        </Button>
      </div>
      {!profiles.length && !credentials.length ? (
        <div className="py-6 text-center text-sm text-muted-foreground">请先添加凭证，再创建路由配置</div>
      ) : !profiles.length ? (
        <div className="py-6 text-center text-sm text-muted-foreground">暂无路由数据，点击"新建配置"创建</div>
      ) : (
        profiles.map((profile) => (
          <div key={profile.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/50 bg-background/50 p-3 text-sm hover:bg-background/80 transition-colors">
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <Badge variant={profile.type === "chat" ? "default" : "outline"} className={profile.type === "chat" ? "bg-primary/20 text-primary border-none" : "bg-blue-500/20 text-blue-400 border-none"}>
                  {profile.type.toUpperCase()}
                </Badge>
                <span className="font-bold text-foreground">{profile.name}</span>
                {profile.is_default && (
                  <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">默认</Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-xs">{providerLabel(profile.provider)} <span className="mx-1">/</span> <span className="font-mono text-primary/80">{profile.model}</span></span>
                {profile.purpose && profile.purpose !== "general" && (
                  <Badge variant="outline" className="bg-violet-500/10 text-violet-400 border-violet-500/30 text-[10px]">{PURPOSE_LABELS[profile.purpose] || profile.purpose}</Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={profile.health_status === "active" ? "default" : profile.health_status === "invalid" ? "destructive" : "outline"} className={profile.health_status === "active" ? "bg-emerald-500/20 text-emerald-400 border-none" : ""}>
                {profile.health_status === "active" ? "Healthy" : profile.health_status === "invalid" ? "Broken" : "Pending"}
              </Badge>
              <div className="flex gap-1.5 border-l border-border/50 pl-3">
                <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-primary/20 hover:text-primary" title="编辑" onClick={() => handleEdit(profile)}>
                  <Pencil className="size-4" />
                </Button>
                <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-primary/20 hover:text-primary" title="重新测试" onClick={() =>
                    api.config.testProfile(profile.id).then((result) => toast.success(result.message || "测试成功")).catch((error) => toast.error(errorMessage(error, "测试失败，请检查 API Key 和服务商是否匹配。"))).finally(onChanged)
                  }>
                  <ShieldCheck className="size-4" />
                </Button>
                <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-destructive/20 hover:text-destructive" title="删除" onClick={() =>
                    api.config.deleteProfile(profile.id).then(() => toast.success("模型配置已删除。")).catch((error) => toast.error(errorMessage(error, "删除失败，请稍后重试。"))).finally(onChanged)
                  }>
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </div>
          </div>
        ))
      )}
      <ModelProfileDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        profile={editingProfile}
        credentials={credentials}
        onChanged={onChanged}
      />
    </div>
  )
}

function ModelProfileDialog({
  open,
  onOpenChange,
  profile,
  credentials,
  onChanged,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  profile: ModelProfile | null
  credentials: ApiCredential[]
  onChanged: () => void
}) {
  const isEdit = !!profile
  const [name, setName] = useState("")
  const [model, setModel] = useState("")
  const [credentialId, setCredentialId] = useState("")
  const [temperature, setTemperature] = useState("0.7")
  const [maxTokens, setMaxTokens] = useState("8192")
  const [purpose, setPurpose] = useState("general")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setName(profile?.name || "")
      setModel(profile?.model || "")
      setCredentialId(profile?.api_credential_id || credentials[0]?.id || "")
      setPurpose(profile?.purpose || "general")
      setTemperature(String(profile?.temperature ?? 0.7))
      setMaxTokens(String(profile?.max_tokens ?? 8192))
    }
  }, [open, profile, credentials])

  const selectedCredential = credentials.find((c) => c.id === credentialId)
  const provider = selectedCredential?.provider || profile?.provider || "openai"

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error("请输入配置名称")
      return
    }
    if (!model.trim()) {
      toast.error("请输入模型名称")
      return
    }
    if (!credentialId) {
      toast.error("请选择关联凭证")
      return
    }

    setSaving(true)
    try {
      const payload = {
        name: name.trim(),
        type: "chat",
        purpose,
        provider,
        model: model.trim(),
        api_credential_id: credentialId,
        temperature: parseFloat(temperature) || 0.7,
        max_tokens: parseInt(maxTokens) || 8192,
        is_active: true,
      }
      if (isEdit) {
        await api.config.updateProfile(profile!.id, payload)
        toast.success("配置已更新")
      } else {
        await api.config.createProfile(payload)
        toast.success("配置已创建")
      }
      onOpenChange(false)
      onChanged()
    } catch (error) {
      toast.error(errorMessage(error, isEdit ? "更新失败，请稍后重试。" : "创建失败，请稍后重试。"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑路由配置" : "新建路由配置"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">配置名称</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="如：DeepSeek-V4-Pro 写作模型"
              disabled={saving}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">模型名称（可自定义）</Label>
            <Input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="如：deepseek-v4-pro、deepseek-v4-auto、gpt-4o"
              disabled={saving}
            />
            <p className="text-xs text-muted-foreground">
              输入服务商支持的模型名，可填入任意模型（如 deepseek-v4-pro）
            </p>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">用途</Label>
            <Select value={purpose} onValueChange={(v) => setPurpose(v || "general")} disabled={saving}>
              <SelectTrigger>
                <SelectValue placeholder="选择用途" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">通用（推荐）</SelectItem>
                <SelectItem value="architecture">架构生成</SelectItem>
                <SelectItem value="outline">大纲生成</SelectItem>
                <SelectItem value="draft">章节草稿</SelectItem>
                <SelectItem value="review">质量审查</SelectItem>
                <SelectItem value="summary">摘要/定稿</SelectItem>
                <SelectItem value="polish">润色</SelectItem>
                <SelectItem value="feedback">反馈</SelectItem>
                <SelectItem value="worldbuilding">世界观</SelectItem>
                <SelectItem value="character">角色</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              选择此配置的用途，不同用途可在项目设置中分别分配
            </p>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">关联凭证</Label>
            <Select value={credentialId} onValueChange={(v) => setCredentialId(v || "")} disabled={saving}>
              <SelectTrigger>
                <SelectValue placeholder="选择凭证" />
              </SelectTrigger>
              <SelectContent>
                {credentials.map((cred) => (
                  <SelectItem key={cred.id} value={cred.id}>
                    {cred.name} ({providerLabel(cred.provider)})
                    {cred.status === "active" ? " ✓" : " (未测试)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Temperature</Label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                disabled={saving}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Max Tokens</Label>
              <Input
                type="number"
                step="256"
                min="256"
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
                disabled={saving}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : isEdit ? "保存" : "创建"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5 font-medium">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  )
}
