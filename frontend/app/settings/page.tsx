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
import { toast } from "sonner"

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-2 text-3xl font-bold">API 设置</h1>
      <p className="mb-6 text-muted-foreground">管理你的 API 凭证和模型配置。Key 加密存储在后端数据库，不会暴露给前端。</p>

      {/* ── API 凭证管理 ── */}
      <ApiCredentialsSection />

      <Separator className="my-6" />

      {/* ── ModelProfile 管理 ── */}
      <ModelProfilesSection />
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
