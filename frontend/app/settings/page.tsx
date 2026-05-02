"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Cpu, Key, Pencil, Plus, Save, TestTube, Trash2 } from "lucide-react"
import { toast } from "sonner"

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
  { value: "general", label: "通用" },
  { value: "architecture", label: "架构生成" },
  { value: "outline", label: "章节目录" },
  { value: "draft", label: "章节草稿" },
  { value: "finalize", label: "定稿" },
  { value: "review", label: "一致性审校" },
  { value: "platform", label: "平台工具" },
]

type DeleteTarget = { type: "llm" | "emb"; name: string } | null

type LLMConfig = {
  interface_format?: string
  model_name?: string
  base_url?: string
  api_key_masked?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  usage?: string
}

type EmbeddingConfig = {
  interface_format?: string
  model_name?: string
  base_url?: string
  api_key_masked?: string
  retrieval_k?: number
}

type LLMForm = {
  name: string
  api_key: string
  base_url: string
  model_name: string
  temperature: number
  max_tokens: number
  timeout: number
  interface_format: string
  usage: string
}

type EmbForm = {
  name: string
  api_key: string
  base_url: string
  model_name: string
  retrieval_k: number
  interface_format: string
}

const defaultLLMForm = (): LLMForm => ({
  name: "",
  api_key: "",
  base_url: "https://api.openai.com/v1",
  model_name: "gpt-4o-mini",
  temperature: 0.7,
  max_tokens: 8192,
  timeout: 600,
  interface_format: "OpenAI",
  usage: "general",
})

const defaultEmbForm = (): EmbForm => ({
  name: "",
  api_key: "",
  base_url: "https://api.openai.com/v1",
  model_name: "text-embedding-ada-002",
  retrieval_k: 4,
  interface_format: "OpenAI",
})

function getProvider(format?: string) {
  return PROVIDER_PRESETS.find((p) => p.value === format)
}

function providerLabel(format?: string) {
  return getProvider(format)?.label || format || "未知"
}

function usageLabel(value?: string) {
  return USAGE_OPTIONS.find((u) => u.value === value)?.label || "通用"
}

function requiresApiKey(format: string) {
  return format.toLowerCase() !== "ollama"
}

function applyProviderPreset<T extends { interface_format: string; base_url: string; model_name: string }>(
  form: T,
  format: string,
  kind: "llm" | "emb"
): T {
  const preset = getProvider(format) || PROVIDER_PRESETS[0]
  return {
    ...form,
    interface_format: format,
    base_url: kind === "llm" ? preset.llmBaseUrl : preset.embBaseUrl,
    model_name: kind === "llm" ? preset.llmModel : preset.embModel,
  }
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

export default function SettingsPage() {
  const [llmConfigs, setLLMConfigs] = useState<Record<string, LLMConfig>>({})
  const [embConfigs, setEmbConfigs] = useState<Record<string, EmbeddingConfig>>({})
  const [llmForm, setLLMForm] = useState<LLMForm>(defaultLLMForm)
  const [embForm, setEmbForm] = useState<EmbForm>(defaultEmbForm)
  const [llmDialogOpen, setLLMDialogOpen] = useState(false)
  const [embDialogOpen, setEmbDialogOpen] = useState(false)
  const [editingLLMName, setEditingLLMName] = useState<string | null>(null)
  const [editingEmbName, setEditingEmbName] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget>(null)

  const loadConfigs = useCallback(async () => {
    const [llm, emb] = await Promise.all([
      api.config.llmList(),
      api.config.embList(),
    ])
    setLLMConfigs(llm)
    setEmbConfigs(emb)
  }, [])

  useEffect(() => {
    void loadConfigs()
  }, [loadConfigs])

  const openAddLLM = () => {
    setEditingLLMName(null)
    setLLMForm(defaultLLMForm())
    setLLMDialogOpen(true)
  }

  const openEditLLM = (name: string, conf: LLMConfig) => {
    setEditingLLMName(name)
    setLLMForm({
      ...defaultLLMForm(),
      name,
      api_key: "",
      base_url: conf.base_url || "",
      model_name: conf.model_name || "",
      temperature: conf.temperature ?? 0.7,
      max_tokens: conf.max_tokens ?? 8192,
      timeout: conf.timeout ?? 600,
      interface_format: conf.interface_format || "OpenAI",
      usage: conf.usage || "general",
    })
    setLLMDialogOpen(true)
  }

  const openAddEmb = () => {
    setEditingEmbName(null)
    setEmbForm(defaultEmbForm())
    setEmbDialogOpen(true)
  }

  const openEditEmb = (name: string, conf: EmbeddingConfig) => {
    setEditingEmbName(name)
    setEmbForm({
      ...defaultEmbForm(),
      name,
      api_key: "",
      base_url: conf.base_url || "",
      model_name: conf.model_name || "",
      retrieval_k: conf.retrieval_k ?? 4,
      interface_format: conf.interface_format || "OpenAI",
    })
    setEmbDialogOpen(true)
  }

  const buildLLMPayload = () => {
    const payload: Record<string, unknown> = {
      name: llmForm.name.trim(),
      api_key: llmForm.api_key.trim(),
      base_url: llmForm.base_url.trim(),
      model_name: llmForm.model_name.trim(),
      temperature: llmForm.temperature,
      max_tokens: llmForm.max_tokens,
      timeout: llmForm.timeout,
      interface_format: llmForm.interface_format,
      usage: llmForm.usage,
    }
    if (editingLLMName) {
      delete payload.name
      if (!payload.api_key) delete payload.api_key
    } else if (!payload.api_key && !requiresApiKey(llmForm.interface_format)) {
      payload.api_key = "ollama"
    }
    return payload
  }

  const buildEmbPayload = () => {
    const payload: Record<string, unknown> = {
      name: embForm.name.trim(),
      api_key: embForm.api_key.trim(),
      base_url: embForm.base_url.trim(),
      model_name: embForm.model_name.trim(),
      retrieval_k: embForm.retrieval_k,
      interface_format: embForm.interface_format,
    }
    if (editingEmbName) {
      delete payload.name
      if (!payload.api_key) delete payload.api_key
    } else if (!payload.api_key && !requiresApiKey(embForm.interface_format)) {
      payload.api_key = "ollama"
    }
    return payload
  }

  const handleSaveLLM = async () => {
    try {
      if (editingLLMName) {
        await api.config.llmUpdate(editingLLMName, buildLLMPayload())
        toast.success("LLM 配置已更新")
      } else {
        await api.config.llmCreate(buildLLMPayload())
        toast.success("LLM 配置已添加")
      }
      setLLMDialogOpen(false)
      setEditingLLMName(null)
      await loadConfigs()
    } catch (error) {
      toast.error(errorMessage(error, "LLM 配置保存失败"))
    }
  }

  const handleSaveEmb = async () => {
    try {
      if (editingEmbName) {
        await api.config.embUpdate(editingEmbName, buildEmbPayload())
        toast.success("Embedding 配置已更新")
      } else {
        await api.config.embCreate(buildEmbPayload())
        toast.success("Embedding 配置已添加")
      }
      setEmbDialogOpen(false)
      setEditingEmbName(null)
      await loadConfigs()
    } catch (error) {
      toast.error(errorMessage(error, "Embedding 配置保存失败"))
    }
  }

  const handleTestLLM = async (name: string) => {
    try {
      const res = await api.config.llmTest(name)
      if (res.success) toast.success(res.message || "测试成功")
      else toast.error(res.message || "测试失败")
    } catch (error) {
      toast.error(errorMessage(error, "测试失败"))
    }
  }

  const handleTestEmb = async (name: string) => {
    try {
      const res = await api.config.embTest(name)
      if (res.success) toast.success(res.message || "测试成功")
      else toast.error(res.message || "测试失败")
    } catch (error) {
      toast.error(errorMessage(error, "测试失败"))
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      if (deleteTarget.type === "llm") {
        await api.config.llmDelete(deleteTarget.name)
      } else {
        await api.config.embDelete(deleteTarget.name)
      }
      toast.success("配置已删除")
      setDeleteTarget(null)
      await loadConfigs()
    } catch (error) {
      toast.error(errorMessage(error, "删除失败"))
    }
  }

  const llmCanSave = Boolean(
    llmForm.name.trim() &&
    llmForm.model_name.trim() &&
    (llmForm.base_url.trim() || llmForm.interface_format === "Gemini") &&
    (editingLLMName || llmForm.api_key.trim() || !requiresApiKey(llmForm.interface_format))
  )
  const embCanSave = Boolean(
    embForm.name.trim() &&
    embForm.model_name.trim() &&
    (embForm.base_url.trim() || embForm.interface_format === "Gemini") &&
    (editingEmbName || embForm.api_key.trim() || !requiresApiKey(embForm.interface_format))
  )

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-8 text-3xl font-bold">API 设置</h1>

      <Tabs defaultValue="llm">
        <TabsList className="mb-6">
          <TabsTrigger value="llm">
            <Cpu className="mr-2 h-4 w-4" />
            LLM
          </TabsTrigger>
          <TabsTrigger value="embedding">
            <Key className="mr-2 h-4 w-4" />
            Embedding
          </TabsTrigger>
        </TabsList>

        <TabsContent value="llm">
          <div className="mb-4 flex justify-end">
            <Button onClick={openAddLLM}>
              <Plus className="mr-2 h-4 w-4" />
              添加 LLM
            </Button>
          </div>

          {Object.keys(llmConfigs).length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">暂无 LLM 配置</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(llmConfigs).map(([name, conf]) => (
                <Card key={name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-base">{name}</CardTitle>
                      <div className="flex items-center gap-1.5">
                        <Badge variant="outline" className="text-xs">{usageLabel(conf.usage)}</Badge>
                        <Badge>{providerLabel(conf.interface_format)}</Badge>
                      </div>
                    </div>
                    <CardDescription className="truncate">{conf.model_name} - {conf.base_url || "默认地址"}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <span>Key: {conf.api_key_masked || "-"}</span>
                      <span>Temp: {conf.temperature ?? "-"}</span>
                      <span>Max Tokens: {conf.max_tokens ?? "-"}</span>
                    </div>
                    <ConfigActions
                      onEdit={() => openEditLLM(name, conf)}
                      onTest={() => handleTestLLM(name)}
                      onDelete={() => setDeleteTarget({ type: "llm", name })}
                    />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="embedding">
          <div className="mb-4 flex justify-end">
            <Button onClick={openAddEmb}>
              <Plus className="mr-2 h-4 w-4" />
              添加 Embedding
            </Button>
          </div>

          {Object.keys(embConfigs).length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">暂无 Embedding 配置</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(embConfigs).map(([name, conf]) => (
                <Card key={name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-base">{name}</CardTitle>
                      <Badge>{providerLabel(conf.interface_format)}</Badge>
                    </div>
                    <CardDescription className="truncate">{conf.model_name} - {conf.base_url || "默认地址"}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-2 text-sm text-muted-foreground">
                      Key: {conf.api_key_masked || "-"} / Top-K: {conf.retrieval_k ?? "-"}
                    </div>
                    <ConfigActions
                      onEdit={() => openEditEmb(name, conf)}
                      onTest={() => handleTestEmb(name)}
                      onDelete={() => setDeleteTarget({ type: "emb", name })}
                    />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={llmDialogOpen} onOpenChange={(open) => { setLLMDialogOpen(open); if (!open) setEditingLLMName(null) }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingLLMName ? "编辑 LLM" : "添加 LLM"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <ConfigInput label="名称" value={llmForm.name} disabled={!!editingLLMName} onChange={(name) => setLLMForm({ ...llmForm, name })} />
            <ProviderSelect value={llmForm.interface_format} onChange={(format) => setLLMForm((form) => applyProviderPreset(form, format, "llm"))} />
            <ConfigInput label="模型" value={llmForm.model_name} onChange={(model_name) => setLLMForm({ ...llmForm, model_name })} />
            <UsageSelect value={llmForm.usage} onChange={(usage) => setLLMForm({ ...llmForm, usage })} />
            <div className="sm:col-span-2">
              <ConfigInput label="Base URL" value={llmForm.base_url} onChange={(base_url) => setLLMForm({ ...llmForm, base_url })} />
            </div>
            <div className="sm:col-span-2">
              <ConfigInput
                label={editingLLMName ? "API Key（留空则不改）" : "API Key"}
                type="password"
                value={llmForm.api_key}
                onChange={(api_key) => setLLMForm({ ...llmForm, api_key })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLLMDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveLLM} disabled={!llmCanSave}>
              <Save className="mr-2 h-4 w-4" />
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={embDialogOpen} onOpenChange={(open) => { setEmbDialogOpen(open); if (!open) setEditingEmbName(null) }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingEmbName ? "编辑 Embedding" : "添加 Embedding"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <ConfigInput label="名称" value={embForm.name} disabled={!!editingEmbName} onChange={(name) => setEmbForm({ ...embForm, name })} />
            <ProviderSelect value={embForm.interface_format} onChange={(format) => setEmbForm((form) => applyProviderPreset(form, format, "emb"))} />
            <ConfigInput label="模型" value={embForm.model_name} onChange={(model_name) => setEmbForm({ ...embForm, model_name })} />
            <NumberInput label="Top-K" value={embForm.retrieval_k} min={1} max={20} onChange={(retrieval_k) => setEmbForm({ ...embForm, retrieval_k })} />
            <div className="sm:col-span-2">
              <ConfigInput label="Base URL" value={embForm.base_url} onChange={(base_url) => setEmbForm({ ...embForm, base_url })} />
            </div>
            <div className="sm:col-span-2">
              <ConfigInput
                label={editingEmbName ? "API Key（留空则不改）" : "API Key"}
                type="password"
                value={embForm.api_key}
                onChange={(api_key) => setEmbForm({ ...embForm, api_key })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmbDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveEmb} disabled={!embCanSave}>
              <Save className="mr-2 h-4 w-4" />
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除配置</DialogTitle>
            <DialogDescription>
              删除 {deleteTarget?.name} 后不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDelete}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ConfigInput({
  label,
  value,
  onChange,
  type = "text",
  disabled = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  disabled?: boolean
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Input type={type} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}

function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  )
}

function ProviderSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div>
      <Label>服务商</Label>
      <Select value={value} onValueChange={(v) => v && onChange(v)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {PROVIDER_PRESETS.map((provider) => (
            <SelectItem key={provider.value} value={provider.value}>{provider.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function UsageSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div>
      <Label>用途</Label>
      <Select value={value} onValueChange={(v) => v && onChange(v)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {USAGE_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function ConfigActions({
  onEdit,
  onTest,
  onDelete,
}: {
  onEdit: () => void
  onTest: () => void
  onDelete: () => void
}) {
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="outline" onClick={onEdit}>
        <Pencil className="mr-1 h-3 w-3" />
        编辑
      </Button>
      <Button size="sm" variant="outline" onClick={onTest}>
        <TestTube className="mr-1 h-3 w-3" />
        测试
      </Button>
      <Button size="sm" variant="ghost" onClick={onDelete}>
        <Trash2 className="mr-1 h-3 w-3" />
        删除
      </Button>
    </div>
  )
}
