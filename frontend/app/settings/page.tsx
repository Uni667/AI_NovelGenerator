"use client"

import { useCallback, useEffect, useState, type ReactNode } from "react"
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  KeyRound,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Wifi,
} from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

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
}

interface Credential {
  id: string
  name: string
  provider: string
  status: string
  api_key_last4?: string
  last_tested_at?: string
}

interface ModelProfile {
  id: string
  name: string
  type: string
  provider: string
  model: string
  health_status: string
  credential_name?: string
  last_tested_at?: string
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
  const [status, setStatus] = useState<ModelStatus | null>(null)
  const [credentials, setCredentials] = useState<Credential[]>([])
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
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-5 p-4 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">模型设置</h1>
          <p className="text-sm text-muted-foreground">配置文本生成模型后，就可以回到项目页生成小说。</p>
        </div>
        <Button variant="outline" onClick={loadAll} disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
          刷新
        </Button>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-6 text-center text-sm text-muted-foreground">正在加载模型状态...</CardContent>
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

      {showAdvanced && (
        <AdvancedSettings
          credentials={credentials}
          profiles={profiles}
          logs={logs}
          onChanged={loadAll}
          onRepair={handleRepair}
        />
      )}
    </main>
  )
}

function EmptyState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>还没有配置文本生成模型</CardTitle>
        <CardDescription>填写 API Key 后，就可以开始生成小说。</CardDescription>
      </CardHeader>
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
    <Card className="border-amber-200 bg-amber-50/60 dark:border-amber-900 dark:bg-amber-950/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="size-5 text-amber-600" />
          模型配置异常
        </CardTitle>
        <CardDescription>当前模型配置不完整或不可用，建议重新测试或清空后重配。</CardDescription>
        {status?.chatErrors?.[0] ? (
          <p className="text-sm text-muted-foreground">{status.chatErrors[0]}</p>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={onRetest} disabled={working === "test"}>
          {working === "test" ? <RefreshCw className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
          重新测试
        </Button>
        <Button variant="outline" onClick={onReset} disabled={working === "reset"}>
          <Trash2 className="size-4" />
          清空模型配置
        </Button>
        <Button variant="outline" onClick={onRepair} disabled={working === "repair"}>
          {working === "repair" ? <RefreshCw className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
          修复旧配置
        </Button>
        <Button variant="ghost" onClick={onToggleAdvanced}>
          {showAdvanced ? "收起高级设置" : "展开高级设置"}
          <ChevronDown className={`size-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
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
    <Card className="border-green-200 bg-green-50/60 dark:border-green-900 dark:bg-green-950/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle className="size-5 text-green-600" />
          文本生成已可用
        </CardTitle>
        <CardDescription className="space-y-1">
          <span className="block">当前服务商：{currentProvider}</span>
          <span className="block">当前文本模型：{status?.chatModel || "未记录"}</span>
          <span className="block">最近测试时间：{formatTime(lastTested)}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={onChangeKey}>
          <KeyRound className="size-4" />
          更换 API Key
        </Button>
        <Button variant="outline" onClick={onRetest} disabled={working === "test"}>
          {working === "test" ? <RefreshCw className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
          重新测试
        </Button>
        <Button variant="outline" onClick={onReset} disabled={working === "reset"}>
          <Trash2 className="size-4" />
          清空模型配置
        </Button>
        <Button variant="ghost" onClick={onToggleAdvanced}>
          {showAdvanced ? "收起高级设置" : "展开高级设置"}
          <ChevronDown className={`size-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
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
    <Card>
      <CardHeader>
        <CardTitle>配置文本生成模型</CardTitle>
        <CardDescription>选择服务商，填写 API Key，然后测试并保存。</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
        <Field label="服务商选择">
          <Select value={provider} onValueChange={(value) => value && setProvider(value)}>
            <SelectTrigger>
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
        <Field label="API Key">
          <Input
            autoComplete="off"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="粘贴服务商提供的 API Key"
          />
        </Field>
        <Button className="self-end" onClick={quickSetup} disabled={saving}>
          {saving ? <RefreshCw className="size-4 animate-spin" /> : <Wifi className="size-4" />}
          测试并保存
        </Button>
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
  credentials: Credential[]
  profiles: ModelProfile[]
  logs: InvocationLog[]
  onChanged: () => void
  onRepair: () => void
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
        高级设置仅用于排查问题，普通用户不需要修改。
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">模型服务账号</CardTitle>
          <CardDescription>这里只显示排查所需的账号状态，不显示凭证编号或完整 Key。</CardDescription>
        </CardHeader>
        <CardContent>
          <CredentialList credentials={credentials} onChanged={onChanged} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">模型配置</CardTitle>
          <CardDescription>文本生成只需要 Chat 类型；Embedding 未配置不会影响小说生成。</CardDescription>
        </CardHeader>
        <CardContent>
          <ProfileList profiles={profiles} onChanged={onChanged} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">排查记录</CardTitle>
          <CardDescription>失败记录只显示简要状态，详细错误请查看服务端日志。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {logs.length ? (
            logs.map((log) => (
              <div key={log.id} className="grid gap-2 rounded-md border p-3 text-sm md:grid-cols-[160px_80px_1fr_80px]">
                <span className="text-muted-foreground">{formatTime(log.created_at)}</span>
                <Badge variant={log.success ? "default" : "destructive"}>{log.success ? "成功" : "失败"}</Badge>
                <span>{providerLabel(log.provider)} / {log.model || "未记录"} / {log.purpose || "general"}</span>
                <span className="text-muted-foreground">{log.success ? `${log.latency_ms || 0}ms` : "调用失败"}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">暂无调用记录。</p>
          )}
          <Button variant="outline" size="sm" onClick={onRepair}>
            <RefreshCw className="size-4" />
            修复旧配置
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

function CredentialList({ credentials, onChanged }: { credentials: Credential[]; onChanged: () => void }) {
  const handleDelete = async (credential: Credential) => {
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

  if (!credentials.length) return <p className="text-sm text-muted-foreground">暂无模型服务账号。</p>

  return (
    <div className="space-y-2">
      {credentials.map((credential) => (
        <div key={credential.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={credential.status === "active" ? "default" : credential.status === "invalid" ? "destructive" : "outline"}>
              {credential.status === "active" ? "可用" : credential.status === "invalid" ? "异常" : "未测试"}
            </Badge>
            <span className="font-medium">{credential.name}</span>
            <span className="text-muted-foreground">{providerLabel(credential.provider)}</span>
            {credential.api_key_last4 ? <Badge variant="secondary">尾号 {credential.api_key_last4}</Badge> : null}
          </div>
          <div className="flex gap-1">
            <IconButton
              title="重新测试"
              onClick={() =>
                api.config
                  .testCredential(credential.id)
                  .then((result) => toast.success(result.message || "测试成功"))
                  .catch((error) => toast.error(errorMessage(error, "测试失败，请检查 API Key 和服务商是否匹配。")))
                  .finally(onChanged)
              }
              icon={<Wifi className="size-4" />}
            />
            <IconButton title="删除" onClick={() => handleDelete(credential)} icon={<Trash2 className="size-4" />} />
          </div>
        </div>
      ))}
    </div>
  )
}

function ProfileList({ profiles, onChanged }: { profiles: ModelProfile[]; onChanged: () => void }) {
  if (!profiles.length) return <p className="text-sm text-muted-foreground">暂无模型配置。</p>

  return (
    <div className="space-y-2">
      {profiles.map((profile) => (
        <div key={profile.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={profile.type === "chat" ? "default" : "outline"}>{profile.type}</Badge>
            <span className="font-medium">{profile.name}</span>
            <span className="text-muted-foreground">{providerLabel(profile.provider)} / {profile.model}</span>
            <Badge variant={profile.health_status === "active" ? "default" : profile.health_status === "invalid" ? "destructive" : "outline"}>
              {profile.health_status === "active" ? "可用" : profile.health_status === "invalid" ? "异常" : "未测试"}
            </Badge>
          </div>
          <div className="flex gap-1">
            <IconButton
              title="重新测试"
              onClick={() =>
                api.config
                  .testProfile(profile.id)
                  .then((result) => toast.success(result.message || "测试成功"))
                  .catch((error) => toast.error(errorMessage(error, "测试失败，请检查 API Key 和服务商是否匹配。")))
                  .finally(onChanged)
              }
              icon={<ShieldCheck className="size-4" />}
            />
            <IconButton
              title="删除"
              onClick={() =>
                api.config
                  .deleteProfile(profile.id)
                  .then(() => toast.success("模型配置已删除。"))
                  .catch((error) => toast.error(errorMessage(error, "删除失败，请稍后重试。")))
                  .finally(onChanged)
              }
              icon={<Trash2 className="size-4" />}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  )
}

function IconButton({ title, icon, onClick }: { title: string; icon: ReactNode; onClick: () => void }) {
  return (
    <Button size="icon" variant="ghost" title={title} aria-label={title} onClick={onClick}>
      {icon}
    </Button>
  )
}
