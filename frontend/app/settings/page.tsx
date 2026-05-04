"use client"

import { useCallback, useEffect, useState } from "react"
import { KeyRound, Plus, RefreshCw, ShieldCheck, SlidersHorizontal, Trash2, Wifi, ChevronDown, AlertTriangle, CheckCircle } from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const PROVIDERS = [
  ["siliconflow", "硅基流动"],
  ["deepseek", "DeepSeek"],
  ["openai", "OpenAI"],
  ["qwen", "通义千问"],
  ["anthropic", "Claude"],
]

const PROVIDER_DISPLAY: Record<string, string> = {
  openai: "OpenAI", deepseek: "DeepSeek", siliconflow: "硅基流动",
  qwen: "通义千问", anthropic: "Claude", custom: "自定义", local: "本地",
}

interface ModelStatus {
  chatReady: boolean
  embeddingReady: boolean
  chatModel: string
  chatProvider: string
  chatErrors: string[]
  activeCredentials: number
  coreReady: boolean
  message: string
}

export default function SettingsPage() {
  const [status, setStatus] = useState<ModelStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [credentials, setCredentials] = useState<any[]>([])
  const [profiles, setProfiles] = useState<any[]>([])
  const [logs, setLogs] = useState<any[]>([])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [s, c, p, l] = await Promise.all([
        api.config.modelStatus().catch(() => null),
        api.config.listCredentials().catch(() => []),
        api.config.listProfiles().catch(() => []),
        api.config.listInvocationLogs(20).catch(() => []),
      ])
      setStatus(s)
      setCredentials(c)
      setProfiles(p)
      setLogs(l)
    } catch {
      // ignore individual failures
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAll() }, [loadAll])

  const handleReset = async () => {
    if (!confirm("确定要清空当前所有模型配置吗？\n\n这将删除 API 凭证和模型配置，但不会影响项目和章节。")) return
    try {
      const r = await api.config.modelReset()
      if (r.success) {
        toast.success(r.message)
        await loadAll()
      }
    } catch (e: any) {
      toast.error(e.message || "清空失败")
    }
  }

  const handleRepair = async () => {
    try {
      const r = await api.config.modelRepair()
      toast.success(r.message)
      if (r.details?.length) {
        r.details.forEach((d: string) => toast.info(d))
      }
      await loadAll()
    } catch (e: any) {
      toast.error(e.message || "修复失败")
    }
  }

  const providerLabel = PROVIDER_DISPLAY[status?.chatProvider || ""] || status?.chatProvider || ""

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">模型设置</h1>
          <p className="text-sm text-muted-foreground">配置文本生成模型后即可开始生成小说。</p>
        </div>
        <Button variant="outline" onClick={loadAll} disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
          刷新
        </Button>
      </div>

      {/* 状态卡 */}
      {loading ? (
        <Card><CardContent className="p-6 text-center text-muted-foreground">加载中...</CardContent></Card>
      ) : !status?.chatReady ? (
        <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-900 dark:bg-amber-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="size-5 text-amber-600" />
              {status?.chatErrors?.length ? "模型配置异常" : "还没有配置文本生成模型"}
            </CardTitle>
            <CardDescription>
              {status?.chatErrors?.length
                ? "当前模型配置不完整或不可用，建议重新测试或清空后重配。"
                : "填写 API Key 后，就可以开始生成小说。"}
            </CardDescription>
            {status?.chatErrors?.length ? (
              <ul className="mt-2 list-inside list-disc text-sm text-muted-foreground">
                {status.chatErrors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            ) : null}
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleReset}>清空模型配置</Button>
            <Button variant="outline" size="sm" onClick={handleRepair}>修复旧配置</Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle className="size-5 text-green-600" />
              文本生成已可用
            </CardTitle>
            <CardDescription>
              <span className="block">服务商：{providerLabel}</span>
              <span className="block">当前模型：{status.chatModel}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleReset}>清空模型配置</Button>
            <Button variant="outline" size="sm" onClick={() => setShowAdvanced(!showAdvanced)}>
              {showAdvanced ? "收起高级设置" : "展开高级设置"}
              <ChevronDown className={`ml-1 size-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 快速配置 */}
      {!status?.chatReady && <QuickSetupCard onDone={loadAll} />}

      {/* 高级设置 */}
      {showAdvanced && (
        <div className="space-y-6">
          <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
            高级设置仅供排查问题使用，普通用户不需要修改。
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><KeyRound className="size-4" />API 凭证管理</CardTitle>
              <CardDescription className="flex items-center gap-2">
                支持多个服务商凭证。
                <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={handleRepair}>修复旧配置</Button>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <CredentialManager credentials={credentials} onChanged={loadAll} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><SlidersHorizontal className="size-4" />模型配置管理</CardTitle>
              <CardDescription>每个配置绑定一个 API 凭证，文本生成只需 Chat 类型。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ProfileManager credentials={credentials} profiles={profiles} onChanged={loadAll} />
            </CardContent>
          </Card>

          {logs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">模型调用日志</CardTitle>
                <CardDescription>记录调用使用的凭证、模型和是否成功。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {logs.map((log) => (
                  <div key={log.id} className="grid gap-2 rounded-md border p-3 text-sm md:grid-cols-[160px_80px_1fr_80px]">
                    <span className="text-muted-foreground">{log.created_at}</span>
                    <Badge variant={log.success ? "default" : "destructive"}>{log.success ? "成功" : "失败"}</Badge>
                    <span>{log.provider} / {log.model} / {log.purpose}</span>
                    <span className="truncate text-muted-foreground">{log.error_message || `${log.latency_ms || 0}ms`}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </main>
  )
}

function QuickSetupCard({ onDone }: { onDone: () => void }) {
  const [provider, setProvider] = useState("siliconflow")
  const [apiKey, setApiKey] = useState("")
  const [loading, setLoading] = useState(false)

  const quickSetup = async () => {
    if (!apiKey.trim()) return toast.error("请输入 API Key")
    setLoading(true)
    try {
      const result = await api.config.modelQuickSetup({ provider, api_key: apiKey.trim() })
      if (result.success) {
        toast.success(result.data.message)
        setApiKey("")
        onDone()
      }
    } catch (error: any) {
      toast.error(error.message || "配置失败，请检查 API Key 和服务商是否匹配。")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">配置文本生成模型</CardTitle>
        <CardDescription>选择一个服务商，填写 API Key，测试通过后即可使用。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-[160px_1fr_auto]">
          <Field label="服务商">
            <Select value={provider} onValueChange={(v) => v && setProvider(v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {PROVIDERS.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="API Key">
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
            />
          </Field>
          <Button className="self-end" onClick={quickSetup} disabled={loading}>
            {loading ? <RefreshCw className="size-4 animate-spin" /> : <Wifi className="size-4" />}
            测试并保存
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          测试通过后自动创建凭证和文本模型配置。知识库向量化（Embedding）可在高级设置中单独配置。
        </p>
      </CardContent>
    </Card>
  )
}

function CredentialManager({ credentials, onChanged }: { credentials: any[]; onChanged: () => void }) {
  const [form, setForm] = useState({ name: "", provider: "openai", api_key: "", base_url: "" })
  const [saving, setSaving] = useState(false)

  const create = async () => {
    if (!form.name.trim()) return toast.error("请输入凭证名称")
    if (form.provider !== "local" && !form.api_key.trim()) return toast.error("请输入 API Key")
    setSaving(true)
    try {
      await api.config.createCredential(form)
      setForm({ name: "", provider: "openai", api_key: "", base_url: "" })
      toast.success("凭证已保存")
      onChanged()
    } catch (error: any) {
      toast.error(error.message || "保存失败")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (cred: any) => {
    try {
      await api.config.deleteCredential(cred.id)
      toast.success("已删除")
      onChanged()
    } catch (error: any) {
      const msg = error.message || ""
      // 如果提示有引用，询问是否级联删除
      if (msg.includes("个模型配置引用") || msg.includes("个模型配置使用")) {
        if (confirm("这个账号正在被模型配置使用，是否一并删除？")) {
          try {
            await api.config.deleteCredential(cred.id, true)
            toast.success("已删除凭证和关联模型配置")
            onChanged()
          } catch (e: any) {
            toast.error(e.message || "删除失败")
          }
        }
      } else {
        toast.error(msg)
      }
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-[1fr_120px_1.2fr_1.2fr_auto]">
        <Field label="名称"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="服务商">
          <Select value={form.provider} onValueChange={(v) => v && setForm({ ...form, provider: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {PROVIDERS.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
              <SelectItem value="custom">自定义</SelectItem>
              <SelectItem value="local">本地</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="API Key"><Input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} /></Field>
        <Field label="Base URL"><Input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="留空使用默认地址" /></Field>
        <Button className="self-end" onClick={create} disabled={saving}><Plus className="size-4" />添加</Button>
      </div>

      <div className="space-y-2">
        {credentials.map((cred) => (
          <div key={cred.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3 text-sm">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <Badge variant={cred.status === "active" ? "default" : cred.status === "invalid" ? "destructive" : "outline"}>{cred.status}</Badge>
              <span className="font-medium">{cred.name}</span>
              <span className="text-muted-foreground">{PROVIDER_DISPLAY[cred.provider] || cred.provider}</span>
              {cred.api_key_last4 && <Badge variant="secondary">****{cred.api_key_last4}</Badge>}
            </div>
            <div className="flex gap-1">
              <IconButton title="测试" onClick={() => api.config.testCredential(cred.id).then((r) => toast.success(r.message)).catch((e) => toast.error(e.message || "测试失败")).finally(onChanged)} icon={<Wifi className="size-4" />} />
              <Button size="sm" variant="ghost" onClick={() => (cred.status === "disabled" ? api.config.enableCredential(cred.id) : api.config.disableCredential(cred.id)).then(onChanged)}>
                {cred.status === "disabled" ? "启用" : "禁用"}
              </Button>
              <IconButton title="删除" onClick={() => handleDelete(cred)} icon={<Trash2 className="size-4" />} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ProfileManager({ credentials, profiles, onChanged }: { credentials: any[]; profiles: any[]; onChanged: () => void }) {
  const firstCred = credentials[0]?.id || ""
  const [form, setForm] = useState({ name: "", type: "chat", purpose: "general", provider: "openai", model: "", api_credential_id: firstCred })

  useEffect(() => { if (!form.api_credential_id && firstCred) setForm((prev) => ({ ...prev, api_credential_id: firstCred })) }, [firstCred, form.api_credential_id])

  const create = async () => {
    if (!form.name.trim() || !form.model.trim()) return toast.error("请输入名称和模型名")
    if (!form.api_credential_id) return toast.error("请先添加 API 凭证")
    try {
      await api.config.createProfile(form)
      setForm({ name: "", type: "chat", purpose: "general", provider: "openai", model: "", api_credential_id: firstCred })
      toast.success("模型配置已创建")
      onChanged()
    } catch (error: any) {
      toast.error(error.message || "创建失败")
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-[1fr_100px_120px_120px_1.2fr_1.2fr_auto]">
        <Field label="名称"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="类型">
          <Select value={form.type} onValueChange={(type) => type && setForm({ ...form, type, purpose: type === "embedding" ? "embedding" : type === "rerank" ? "rerank" : "general" })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="chat">Chat</SelectItem><SelectItem value="embedding">Embedding</SelectItem><SelectItem value="rerank">Rerank</SelectItem></SelectContent>
          </Select>
        </Field>
        <Field label="用途">
          <Input value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
        </Field>
        <Field label="服务商">
          <Select value={form.provider} onValueChange={(v) => v && setForm({ ...form, provider: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {PROVIDERS.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
              <SelectItem value="custom">自定义</SelectItem>
              <SelectItem value="local">本地</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="模型名"><Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="如 deepseek-v4-flash" /></Field>
        <Field label="绑定凭证">
          <Select value={form.api_credential_id} onValueChange={(id) => id && setForm({ ...form, api_credential_id: id })}>
            <SelectTrigger><SelectValue placeholder="选择凭证" /></SelectTrigger>
            <SelectContent>{credentials.map((c) => <SelectItem key={c.id} value={c.id}>{c.name} ({c.provider})</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <Button className="self-end" onClick={create}><Plus className="size-4" />新增</Button>
      </div>

      <div className="space-y-2">
        {profiles.map((profile) => (
          <div key={profile.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3 text-sm">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <Badge>{profile.type}</Badge>
              <span className="font-medium">{profile.name}</span>
              <span className="text-muted-foreground">{profile.model}</span>
              <Badge variant="outline">{profile.credential_name || "未绑定"}</Badge>
              <Badge variant={profile.health_status === "active" ? "default" : profile.health_status === "invalid" ? "destructive" : "outline"}>{profile.health_status}</Badge>
            </div>
            <div className="flex gap-1">
              <IconButton title="测试" onClick={() => api.config.testProfile(profile.id).then((r) => toast.success(r.message)).catch((e) => toast.error(e.message || "测试失败")).finally(onChanged)} icon={<ShieldCheck className="size-4" />} />
              <Button size="sm" variant="ghost" onClick={() => api.config.setDefaultProfile(profile.id).then(onChanged)}>默认</Button>
              <IconButton title="删除" onClick={() => api.config.deleteProfile(profile.id).then(onChanged).catch((e) => toast.error(e.message || "删除失败"))} icon={<Trash2 className="size-4" />} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1"><Label className="text-xs">{label}</Label>{children}</div>
}

function IconButton({ title, icon, onClick }: { title: string; icon: React.ReactNode; onClick: () => void }) {
  return <Button size="icon" variant="ghost" title={title} aria-label={title} onClick={onClick}>{icon}</Button>
}
