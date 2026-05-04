"use client"

import { useCallback, useEffect, useState } from "react"

import { api } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AlertTriangle, CheckCircle, Cpu, Eye, EyeOff, Key, Loader2, Pencil, Save, ShieldCheck, TestTube, Trash2, XCircle } from "lucide-react"
import { toast } from "sonner"

const PROVIDERS = [
  { value: "openai", label: "OpenAI", defaultBaseUrl: "https://api.openai.com/v1", defaultChatModel: "gpt-4o-mini", defaultEmbModel: "text-embedding-ada-002" },
  { value: "deepseek", label: "DeepSeek", defaultBaseUrl: "https://api.deepseek.com", defaultChatModel: "deepseek-chat", defaultEmbModel: "" },
  { value: "qwen", label: "通义千问", defaultBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", defaultChatModel: "qwen-plus", defaultEmbModel: "text-embedding-v3" },
  { value: "anthropic", label: "Anthropic", defaultBaseUrl: "https://api.anthropic.com/v1", defaultChatModel: "claude-sonnet-4-6", defaultEmbModel: "" },
  { value: "custom", label: "自定义接口", defaultBaseUrl: "", defaultChatModel: "", defaultEmbModel: "" },
]

interface ApiConfig {
  configured: boolean
  provider: string
  api_key_masked: string
  api_key_last4: string
  base_url: string
  default_chat_model: string
  default_embedding_model: string
  default_model: string
  status: "active" | "invalid" | "untested"
  last_tested_at: string | null
  last_used_at: string | null
  updated_at: string
}

export default function SettingsPage() {
  // 当前配置状态
  const [config, setConfig] = useState<ApiConfig | null>(null)
  const [loading, setLoading] = useState(true)

  // 编辑表单
  const [editing, setEditing] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [form, setForm] = useState({
    provider: "openai",
    api_key: "",
    base_url: "https://api.openai.com/v1",
    default_chat_model: "gpt-4o-mini",
    default_embedding_model: "text-embedding-ada-002",
  })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadConfig = useCallback(async () => {
    try {
      const data = await api.config.get()
      setConfig(data)
    } catch {
      // 忽略加载错误
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  const handleProviderChange = (provider: string) => {
    const preset = PROVIDERS.find((p) => p.value === provider)
    setForm({
      ...form,
      provider,
      base_url: preset?.defaultBaseUrl || "",
      default_chat_model: preset?.defaultChatModel || "",
      default_embedding_model: preset?.defaultEmbModel || "",
    })
  }

  const handleChangeKey = () => {
    const preset = PROVIDERS.find((p) => p.value === (config?.provider || "openai"))
    setForm({
      provider: config?.provider || "openai",
      api_key: "",
      base_url: config?.base_url || preset?.defaultBaseUrl || "",
      default_chat_model: config?.default_chat_model || preset?.defaultChatModel || "",
      default_embedding_model: config?.default_embedding_model || preset?.defaultEmbModel || "",
    })
    setEditing(true)
  }

  const handleStartAdd = () => {
    if (!config?.configured) {
      setEditing(true)
    } else {
      handleChangeKey()
    }
  }

  const handleSave = async () => {
    if (!form.api_key.trim()) {
      toast.error("API Key 不能为空")
      return
    }
    setSaving(true)
    try {
      const result = await api.config.save({
        provider: form.provider,
        api_key: form.api_key.trim(),
        base_url: form.base_url.trim() || undefined,
        default_chat_model: form.default_chat_model.trim() || undefined,
        default_embedding_model: form.default_embedding_model.trim() || undefined,
      })
      setConfig(result)
      setEditing(false)
      setShowKey(false)
      toast.success("API 配置已保存")
    } catch (err: any) {
      toast.error(err.message || "保存失败")
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      const result = await api.config.test()
      if (result.success) {
        toast.success(result.message)
      } else {
        toast.error(result.message)
      }
      // 重新加载以获取最新状态
      await loadConfig()
    } catch (err: any) {
      toast.error(err.message || "测试失败")
    } finally {
      setTesting(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm("确定要删除 API 配置吗？删除后需要重新配置才能使用生成功能。")) return
    setDeleting(true)
    try {
      await api.config.delete()
      setConfig({ configured: false } as ApiConfig)
      setEditing(false)
      toast.success("API 配置已删除")
    } catch (err: any) {
      toast.error(err.message || "删除失败")
    } finally {
      setDeleting(false)
    }
  }

  const statusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500 hover:bg-green-600"><CheckCircle className="mr-1 h-3 w-3" />可用</Badge>
      case "invalid":
        return <Badge variant="destructive"><XCircle className="mr-1 h-3 w-3" />不可用</Badge>
      default:
        return <Badge variant="secondary"><AlertTriangle className="mr-1 h-3 w-3" />未测试</Badge>
    }
  }

  const providerLabel = (provider: string) =>
    PROVIDERS.find((p) => p.value === provider)?.label || provider

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl py-8 text-center text-muted-foreground">
        <Loader2 className="mx-auto h-6 w-6 animate-spin mb-2" />
        加载中...
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-2 text-3xl font-bold">API 设置</h1>
      <p className="mb-6 text-muted-foreground">管理你的 API 凭证和模型配置。Key 加密存储在后端数据库，不会暴露给前端。</p>

      {/* ── API 凭证管理 ── */}
      <ApiCredentialsSection />

      <Separator className="my-6" />

      {/* ── 快速配置（单 Key 兼容） ── */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                我的 API 配置
              </CardTitle>
              <CardDescription>API Key 与你的账号绑定，加密保存在服务器端</CardDescription>
            </div>
            {config?.configured ? statusBadge(config.status) : (
              <Badge variant="outline" className="text-muted-foreground">未配置</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {!config?.configured ? (
            <div className="py-4 text-center">
              <Key className="mx-auto h-10 w-10 text-muted-foreground mb-2" />
              <p className="text-muted-foreground mb-3">尚未配置 API Key</p>
              <Button onClick={handleStartAdd} disabled={editing}>
                <Key className="mr-2 h-4 w-4" /> 开始配置
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">服务商</span>
                  <p className="font-medium">{providerLabel(config.provider)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">API Key</span>
                  <p className="font-medium font-mono">{config.api_key_masked}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">聊天模型</span>
                  <p className="font-medium">{config.default_chat_model || config.default_model || "-"}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Embedding 模型</span>
                  <p className="font-medium">{config.default_embedding_model || "未配置"}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-muted-foreground">Base URL</span>
                  <p className="font-medium text-xs truncate">{config.base_url || "-"}</p>
                </div>
              </div>

              {config.updated_at && (
                <p className="text-xs text-muted-foreground">
                  更新时间: {new Date(config.updated_at).toLocaleString("zh-CN")}
                  {config.last_used_at && ` / 上次使用: ${new Date(config.last_used_at).toLocaleString("zh-CN")}`}
                </p>
              )}

              <div className="flex flex-wrap gap-2 pt-1">
                <Button variant="outline" size="sm" onClick={handleChangeKey}>
                  <Pencil className="mr-1 h-4 w-4" /> 更换 Key
                </Button>
                <Button variant="outline" size="sm" onClick={handleTest} disabled={testing}>
                  {testing ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <TestTube className="mr-1 h-4 w-4" />}
                  测试连接
                </Button>
                <Button variant="ghost" size="sm" onClick={handleDelete} disabled={deleting}>
                  <Trash2 className="mr-1 h-4 w-4" /> 删除
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 编辑表单 ── */}
      {editing && (
        <Card>
          <CardHeader>
            <CardTitle>
              {config?.configured ? "更换 API Key" : "配置 API Key"}
            </CardTitle>
            <CardDescription>Key 仅保存在服务器端加密数据库，前端不会暴露完整内容</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>服务商</Label>
              <Select value={form.provider} onValueChange={(v) => v && handleProviderChange(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>API Key</Label>
              <div className="flex gap-2">
                <Input
                  type={showKey ? "text" : "password"}
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder={config?.configured ? "输入新 Key（留空则保留原有）" : "输入完整 API Key"}
                />
                <Button variant="outline" size="icon" onClick={() => setShowKey(!showKey)}>
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              {config?.configured && (
                <p className="text-xs text-muted-foreground mt-1">
                  留空则保留已有 Key ({config.api_key_masked})
                </p>
              )}
            </div>

            <div>
              <Label>Base URL</Label>
              <Input
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
              />
            </div>

            <div>
              <Label>默认聊天模型</Label>
              <Input
                value={form.default_chat_model}
                onChange={(e) => setForm({ ...form, default_chat_model: e.target.value })}
                placeholder="gpt-4o-mini"
              />
            </div>

            <div>
              <Label>默认 Embedding 模型（可选）</Label>
              <Input
                value={form.default_embedding_model}
                onChange={(e) => setForm({ ...form, default_embedding_model: e.target.value })}
                placeholder="text-embedding-ada-002（留空则禁用向量化）"
              />
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              <Button onClick={handleSave} disabled={saving || !form.api_key.trim()}>
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                保存配置
              </Button>
              <Button variant="outline" onClick={() => setEditing(false)}>取消</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── ModelProfile 管理 ── */}
      <ModelProfilesSection />

      <Separator className="my-8" />

      {/* ── 迁移旧配置 ── */}
      <MigrateLegacySection />

      {/* ── 高级：多 LLM 配置（旧系统兼容） ── */}
      <AdvancedLLMSection />
    </div>
  )
}

function AdvancedLLMSection() {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setOpen(true)}>
        高级：多用途 LLM 配置（兼容旧版）
      </Button>
    )
  }

  return (
    <LegacyLLMConfigSection onClose={() => setOpen(false)} />
  )
}

// ── 以下为旧版多 LLM/Embedding 配置（向后兼容） ──

function LegacyLLMConfigSection({ onClose }: { onClose: () => void }) {
  const PROVIDER_PRESETS = [
    { value: "OpenAI", label: "OpenAI", llmBaseUrl: "https://api.openai.com/v1", llmModel: "gpt-4o-mini", embBaseUrl: "https://api.openai.com/v1", embModel: "text-embedding-ada-002" },
    { value: "DeepSeek", label: "DeepSeek", llmBaseUrl: "https://api.deepseek.com", llmModel: "deepseek-chat", embBaseUrl: "https://api.openai.com/v1", embModel: "text-embedding-ada-002" },
    { value: "SiliconFlow", label: "SiliconFlow", llmBaseUrl: "https://api.siliconflow.cn/v1", llmModel: "deepseek-ai/DeepSeek-V3", embBaseUrl: "https://api.siliconflow.cn/v1/embeddings", embModel: "BAAI/bge-m3" },
    { value: "Ollama", label: "Ollama", llmBaseUrl: "http://localhost:11434", llmModel: "llama3.1", embBaseUrl: "http://localhost:11434", embModel: "nomic-embed-text" },
    { value: "Gemini", label: "Gemini", llmBaseUrl: "", llmModel: "gemini-1.5-flash", embBaseUrl: "", embModel: "text-embedding-004" },
    { value: "Azure OpenAI", label: "Azure OpenAI", llmBaseUrl: "https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-02-15-preview", llmModel: "<deployment>", embBaseUrl: "https://<resource>.openai.azure.com/openai/deployments/<deployment>/embeddings?api-version=2024-02-15-preview", embModel: "<deployment>" },
    { value: "ML Studio", label: "LM Studio", llmBaseUrl: "http://localhost:1234/v1", llmModel: "local-model", embBaseUrl: "http://localhost:1234/v1", embModel: "local-embedding" },
    { value: "Volcengine", label: "火山引擎", llmBaseUrl: "https://ark.cn-beijing.volces.com/api/v3", llmModel: "", embBaseUrl: "https://ark.cn-beijing.volces.com/api/v3", embModel: "" },
    { value: "Alibaba Bailian", label: "阿里云百炼", llmBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", llmModel: "qwen-plus", embBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", embModel: "text-embedding-v3" },
  ]

  const USAGE_OPTIONS = [
    { value: "general", label: "通用" }, { value: "architecture", label: "架构生成" },
    { value: "outline", label: "章节目录" }, { value: "draft", label: "章节草稿" },
    { value: "finalize", label: "定稿" }, { value: "review", label: "一致性审校" },
    { value: "platform", label: "平台工具" },
  ]

  const [llmConfigs, setLLMConfigs] = useState<Record<string, any>>({})
  const [embConfigs, setEmbConfigs] = useState<Record<string, any>>({})
  const [llmForm, setLLMForm] = useState<any>({ name: "", api_key: "", base_url: "https://api.openai.com/v1", model_name: "gpt-4o-mini", temperature: 0.7, max_tokens: 8192, timeout: 600, interface_format: "OpenAI", usage: "general" })
  const [embForm, setEmbForm] = useState<any>({ name: "", api_key: "", base_url: "https://api.openai.com/v1", model_name: "text-embedding-ada-002", retrieval_k: 4, interface_format: "OpenAI" })
  const [editingLLM, setEditingLLM] = useState<string | null>(null)
  const [editingEmb, setEditingEmb] = useState<string | null>(null)
  const [dialog, setDialog] = useState<"" | "llm" | "emb">("")
  const [delTarget, setDelTarget] = useState<{ type: "llm" | "emb"; name: string } | null>(null)

  const load = useCallback(async () => {
    try { setLLMConfigs(await api.config.llmList()) } catch {}
    try { setEmbConfigs(await api.config.embList()) } catch {}
  }, [])

  useEffect(() => { load() }, [load])

  const defaultLLMForm = () => ({ name: "", api_key: "", base_url: "https://api.openai.com/v1", model_name: "gpt-4o-mini", temperature: 0.7, max_tokens: 8192, timeout: 600, interface_format: "OpenAI", usage: "general" })
  const defaultEmbForm = () => ({ name: "", api_key: "", base_url: "https://api.openai.com/v1", model_name: "text-embedding-ada-002", retrieval_k: 4, interface_format: "OpenAI" })

  const openLLM = (name?: string, conf?: any) => {
    if (name && conf) {
      setEditingLLM(name)
      setLLMForm({ ...defaultLLMForm(), name, api_key: "", base_url: conf.base_url || "", model_name: conf.model_name || "", temperature: conf.temperature ?? 0.7, max_tokens: conf.max_tokens ?? 8192, timeout: conf.timeout ?? 600, interface_format: conf.interface_format || "OpenAI", usage: conf.usage || "general" })
    } else {
      setEditingLLM(null)
      setLLMForm(defaultLLMForm())
    }
    setDialog("llm")
  }
  const openEmb = (name?: string, conf?: any) => {
    if (name && conf) {
      setEditingEmb(name)
      setEmbForm({ ...defaultEmbForm(), name, api_key: "", base_url: conf.base_url || "", model_name: conf.model_name || "", retrieval_k: conf.retrieval_k ?? 4, interface_format: conf.interface_format || "OpenAI" })
    } else {
      setEditingEmb(null)
      setEmbForm(defaultEmbForm())
    }
    setDialog("emb")
  }

  const saveLLM = async () => {
    try {
      const payload: any = { name: llmForm.name.trim(), api_key: llmForm.api_key.trim(), base_url: llmForm.base_url.trim(), model_name: llmForm.model_name.trim(), temperature: llmForm.temperature, max_tokens: llmForm.max_tokens, timeout: llmForm.timeout, interface_format: llmForm.interface_format, usage: llmForm.usage }
      if (editingLLM) { delete payload.name; if (!payload.api_key) delete payload.api_key }
      if (editingLLM) await api.config.llmUpdate(editingLLM, payload)
      else await api.config.llmCreate(payload)
      toast.success(editingLLM ? "已更新" : "已添加")
      setDialog(""); setEditingLLM(null); await load()
    } catch (e: any) { toast.error(e.message || "保存失败") }
  }
  const saveEmb = async () => {
    try {
      const payload: any = { name: embForm.name.trim(), api_key: embForm.api_key.trim(), base_url: embForm.base_url.trim(), model_name: embForm.model_name.trim(), retrieval_k: embForm.retrieval_k, interface_format: embForm.interface_format }
      if (editingEmb) { delete payload.name; if (!payload.api_key) delete payload.api_key }
      if (editingEmb) await api.config.embUpdate(editingEmb, payload)
      else await api.config.embCreate(payload)
      toast.success(editingEmb ? "已更新" : "已添加")
      setDialog(""); setEditingEmb(null); await load()
    } catch (e: any) { toast.error(e.message || "保存失败") }
  }

  const testLLM = async (name: string) => {
    try { const r = await api.config.llmTest(name); r.success ? toast.success(r.message) : toast.error(r.message) } catch (e: any) { toast.error(e.message) }
  }
  const testEmb = async (name: string) => {
    try { const r = await api.config.embTest(name); r.success ? toast.success(r.message) : toast.error(r.message) } catch (e: any) { toast.error(e.message) }
  }
  const del = async () => {
    if (!delTarget) return
    try {
      if (delTarget.type === "llm") await api.config.llmDelete(delTarget.name)
      else await api.config.embDelete(delTarget.name)
      toast.success("已删除"); setDelTarget(null); await load()
    } catch (e: any) { toast.error(e.message || "删除失败") }
  }

  const applyPreset = (form: any, format: string, kind: "llm" | "emb") => {
    const p = PROVIDER_PRESETS.find(x => x.value === format) || PROVIDER_PRESETS[0]
    return { ...form, interface_format: format, base_url: kind === "llm" ? p.llmBaseUrl : p.embBaseUrl, model_name: kind === "llm" ? p.llmModel : p.embModel }
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-semibold">高级 LLM/Embedding 配置</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>收起</Button>
      </div>
      <Tabs defaultValue="llm">
        <TabsList className="mb-4">
          <TabsTrigger value="llm"><Cpu className="mr-2 h-4 w-4" />LLM</TabsTrigger>
          <TabsTrigger value="embedding"><Key className="mr-2 h-4 w-4" />Embedding</TabsTrigger>
        </TabsList>
        <TabsContent value="llm">
          <div className="flex justify-end mb-3"><Button size="sm" onClick={() => openLLM()}>添加 LLM</Button></div>
          {Object.keys(llmConfigs).length === 0 ? <p className="text-muted-foreground text-sm py-4">暂无</p> :
            <div className="space-y-2">{Object.entries(llmConfigs).map(([name, c]) => (
              <Card key={name}><CardHeader className="pb-1"><CardTitle className="text-sm">{name}</CardTitle></CardHeader>
                <CardContent><div className="text-xs text-muted-foreground mb-1">Key: {c.api_key_masked} / {c.model_name} / {c.base_url}</div>
                  <div className="flex gap-1"><Button size="sm" variant="ghost" onClick={() => openLLM(name, c)}>编辑</Button><Button size="sm" variant="ghost" onClick={() => testLLM(name)}>测试</Button><Button size="sm" variant="ghost" onClick={() => setDelTarget({ type: "llm", name })}>删除</Button></div></CardContent></Card>
            ))}</div>}
        </TabsContent>
        <TabsContent value="embedding">
          <div className="flex justify-end mb-3"><Button size="sm" onClick={() => openEmb()}>添加</Button></div>
          {Object.keys(embConfigs).length === 0 ? <p className="text-muted-foreground text-sm py-4">暂无</p> :
            <div className="space-y-2">{Object.entries(embConfigs).map(([name, c]) => (
              <Card key={name}><CardHeader className="pb-1"><CardTitle className="text-sm">{name}</CardTitle></CardHeader>
                <CardContent><div className="text-xs text-muted-foreground mb-1">Key: {c.api_key_masked} / {c.model_name}</div>
                  <div className="flex gap-1"><Button size="sm" variant="ghost" onClick={() => openEmb(name, c)}>编辑</Button><Button size="sm" variant="ghost" onClick={() => testEmb(name)}>测试</Button><Button size="sm" variant="ghost" onClick={() => setDelTarget({ type: "emb", name })}>删除</Button></div></CardContent></Card>
            ))}</div>}
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ── ModelProfile 管理 ──

function ModelProfilesSection() {
  const [profiles, setProfiles] = useState<any[]>([])
  const [loaded, setLoaded] = useState(false)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: "", type: "chat", provider: "openai", base_url: "", model: "" })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try { setProfiles(await api.config.listProfiles()); setLoaded(true) } catch {}
  }, [])

  useEffect(() => { if (open) load() }, [open, load])

  const handleCreate = async () => {
    if (!form.name.trim() || !form.model.trim()) { toast.error("名称和模型不能为空"); return }
    setSaving(true)
    try { await api.config.createProfile(form); toast.success("已创建"); setForm({ name: "", type: "chat", provider: "openai", base_url: "", model: "" }); load() }
    catch (e: any) { toast.error(e.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("删除该模型配置？")) return
    try { await api.config.deleteProfile(id); toast.success("已删除"); load() }
    catch (e: any) { toast.error(e.message) }
  }

  const handleTest = async (id: string) => {
    try { const r = await api.config.testProfile(id); r.success ? toast.success(r.message) : toast.error(r.message) }
    catch (e: any) { toast.error(e.message) }
  }

  if (!open) {
    return <Button variant="ghost" size="sm" className="text-muted-foreground mt-4" onClick={() => setOpen(true)}>管理模型配置（ModelProfile）</Button>
  }

  return (
    <Card className="mt-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">模型配置（ModelProfile）</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>收起</Button>
        </div>
        <CardDescription>不保存 API Key，仅定义模型名和用途。API Key 统一来自上方配置。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2 flex-wrap">
          <Input className="w-32" placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <Select value={form.type} onValueChange={v => v && setForm({ ...form, type: v })}>
            <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="chat">Chat</SelectItem><SelectItem value="embedding">Embedding</SelectItem></SelectContent>
          </Select>
          <Select value={form.provider} onValueChange={v => v && setForm({ ...form, provider: v })}>
            <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="openai">OpenAI</SelectItem><SelectItem value="deepseek">DeepSeek</SelectItem>
              <SelectItem value="qwen">Qwen</SelectItem><SelectItem value="anthropic">Anthropic</SelectItem>
              <SelectItem value="custom">自定义</SelectItem>
            </SelectContent>
          </Select>
          <Input className="w-40" placeholder="模型名" value={form.model} onChange={e => setForm({ ...form, model: e.target.value })} />
          <Input className="w-40" placeholder="Base URL（可选）" value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })} />
          <Button size="sm" onClick={handleCreate} disabled={saving}>添加</Button>
        </div>

        {!loaded ? <p className="text-xs text-muted-foreground">加载中...</p> :
          profiles.length === 0 ? <p className="text-xs text-muted-foreground">暂无模型配置</p> :
            <div className="space-y-1">{
              profiles.map(p => (
                <div key={p.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant={p.type === "chat" ? "default" : "secondary"}>{p.type}</Badge>
                    <span className="font-medium">{p.name}</span>
                    <span className="text-muted-foreground">{p.model}</span>
                    {p.is_active ? null : <Badge variant="outline" className="text-xs">已停用</Badge>}
                  </div>
                  <div className="flex gap-1">
                    <Button size="sm" variant="ghost" onClick={() => handleTest(p.id)}>测试</Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(p.id)}>删除</Button>
                  </div>
                </div>
              ))
            }</div>
        }
      </CardContent>
    </Card>
  )
}

// ── 迁移旧配置 ──

function MigrateLegacySection() {
  const [migrating, setMigrating] = useState(false)
  const handleMigrate = async () => {
    if (!confirm("将旧版 LLM/Embedding 配置迁移为 ModelProfile？\nAPI Key 不会迁移，仅迁移模型名和用途。")) return
    setMigrating(true)
    try { const r = await api.config.migrate(); toast.success(r.message) }
    catch (e: any) { toast.error(e.message) }
    finally { setMigrating(false) }
  }

  return (
    <div className="text-center">
      <Button variant="outline" size="sm" onClick={handleMigrate} disabled={migrating}>
        {migrating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        迁移旧版 LLM 配置
      </Button>
      <p className="text-xs text-muted-foreground mt-1">将旧的 LLM/Embedding 配置转为 ModelProfile，API Key 不再迁移</p>
    </div>
  )
}

// ── API 凭证管理器（多凭证支持）──

function ApiCredentialsSection() {
  const [creds, setCreds] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState({ name: "", provider: "openai", api_key: "", base_url: "https://api.openai.com/v1" })
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    try { setCreds(await api.config.listCredentials()); setLoading(false) } catch { setLoading(false) }
  }, [])

  useEffect(() => { if (expanded) load() }, [expanded, load])

  const handleCreate = async () => {
    if (!form.name.trim() || !form.api_key.trim()) { toast.error("名称和 API Key 不能为空"); return }
    setSaving(true)
    try { await api.config.createCredential(form); toast.success("凭证已创建"); setShowForm(false); setForm({ name: "", provider: "openai", api_key: "", base_url: "https://api.openai.com/v1" }); load() }
    catch (e: any) { toast.error(e.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("删除该凭证？")) return
    try { await api.config.deleteCredential(id); toast.success("已删除"); load() }
    catch (e: any) { toast.error(e.message) }
  }

  const handleTest = async (id: string) => {
    try { const r = await api.config.testCredential(id); r.success ? toast.success(r.message) : toast.error(r.message); load() }
    catch (e: any) { toast.error(e.message) }
  }

  const handleToggle = async (id: string, enable: boolean) => {
    try {
      if (enable) await api.config.enableCredential(id)
      else await api.config.disableCredential(id)
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  if (!expanded) {
    return (
      <Card className="mb-4">
        <CardContent className="p-4">
          <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpanded(true)}>
            <div>
              <h3 className="font-semibold text-lg">API 凭证</h3>
              <p className="text-sm text-muted-foreground">{loading ? "加载中..." : `${creds.length} 个凭证`}</p>
            </div>
            <Button variant="ghost" size="sm">展开</Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const statusBadge = (s: string) => {
    const map: Record<string, { v: string; c: string }> = {
      active: { v: "可用", c: "bg-green-500" },
      invalid: { v: "不可用", c: "bg-red-500" },
      untested: { v: "未测试", c: "bg-yellow-500" },
      disabled: { v: "已禁用", c: "bg-gray-500" },
    }
    const m = map[s] || map.untested
    return <Badge className={m.c}>{m.v}</Badge>
  }

  const providerLabel = (p: string) => ({ openai: "OpenAI", deepseek: "DeepSeek", qwen: "通义千问", anthropic: "Anthropic", custom: "自定义", local: "本地" } as any)[p] || p

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">API 凭证 ({creds.length})</CardTitle>
            <CardDescription>支持多个 API 接入源。创建凭证后，在下方模型配置中绑定。</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setShowForm(!showForm)}>{showForm ? "取消" : "添加凭证"}</Button>
            <Button size="sm" variant="ghost" onClick={() => setExpanded(false)}>收起</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {showForm && (
          <div className="flex gap-2 flex-wrap items-end rounded border p-3 bg-muted/30">
            <div>
              <Label className="text-xs">名称</Label>
              <Input className="w-28 h-8 text-xs" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="My Key" />
            </div>
            <div>
              <Label className="text-xs">服务商</Label>
              <Select value={form.provider} onValueChange={v => { if (!v) return; const urls: Record<string, string> = { openai: "https://api.openai.com/v1", deepseek: "https://api.deepseek.com", qwen: "https://dashscope.aliyuncs.com/compatible-mode/v1", anthropic: "https://api.anthropic.com/v1", custom: "", local: "http://localhost:11434" }; setForm({ ...form, provider: v, base_url: urls[v] || "" }); }}>
                <SelectTrigger className="w-24 h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI</SelectItem><SelectItem value="deepseek">DeepSeek</SelectItem>
                  <SelectItem value="qwen">Qwen</SelectItem><SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="custom">自定义</SelectItem><SelectItem value="local">本地</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">API Key</Label>
              <Input className="w-40 h-8 text-xs" type="password" value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." />
            </div>
            <div>
              <Label className="text-xs">Base URL</Label>
              <Input className="w-36 h-8 text-xs" value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })} />
            </div>
            <Button size="sm" onClick={handleCreate} disabled={saving}>保存</Button>
          </div>
        )}

        {loading ? <p className="text-xs text-muted-foreground">加载中...</p> :
          creds.length === 0 ? <p className="text-xs text-muted-foreground">暂无凭证，添加一个开始使用</p> :
            <div className="space-y-1">
              {creds.map(c => (
                <div key={c.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
                  <div className="flex items-center gap-2 min-w-0">
                    {statusBadge(c.status)}
                    <span className="font-medium">{c.name}</span>
                    <Badge variant="outline" className="text-xs">{providerLabel(c.provider)}</Badge>
                    <span className="text-muted-foreground text-xs truncate max-w-[120px]">{c.base_url}</span>
                    {c.is_default && <Badge variant="secondary" className="text-xs">默认</Badge>}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button size="sm" variant="ghost" onClick={() => handleTest(c.id)}>测试</Button>
                    <Button size="sm" variant="ghost" onClick={() => handleToggle(c.id, c.status === "disabled")}>
                      {c.status === "disabled" ? "启用" : "禁用"}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(c.id)}>删除</Button>
                  </div>
                </div>
              ))}
            </div>
        }
      </CardContent>
    </Card>
  )
}

// ── ModelProfile 管理 ──
