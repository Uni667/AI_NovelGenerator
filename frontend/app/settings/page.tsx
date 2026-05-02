"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Cpu, Key, Plus, TestTube, Trash2 } from "lucide-react"
import { toast } from "sonner"

const INTERFACE_FORMATS = [
  "OpenAI",
  "Azure OpenAI",
  "Ollama",
  "DeepSeek",
  "Gemini",
  "ML Studio",
  "SiliconFlow",
  "Volcengine",
  "Alibaba Bailian",
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
  usage?: string
}

type EmbeddingConfig = {
  interface_format?: string
  model_name?: string
  base_url?: string
  api_key_masked?: string
  retrieval_k?: number
}

export default function SettingsPage() {
  const [llmConfigs, setLLMConfigs] = useState<Record<string, LLMConfig>>({})
  const [embConfigs, setEmbConfigs] = useState<Record<string, EmbeddingConfig>>({})
  const [newLLM, setNewLLM] = useState({
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
  const [newEmb, setNewEmb] = useState({
    name: "",
    api_key: "",
    base_url: "https://api.openai.com/v1",
    model_name: "text-embedding-ada-002",
    retrieval_k: 4,
    interface_format: "OpenAI",
  })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [embDialogOpen, setEmbDialogOpen] = useState(false)
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

  const handleAddLLM = async () => {
    await api.config.llmCreate(newLLM)
    toast.success("LLM config added")
    setDialogOpen(false)
    await loadConfigs()
  }

  const handleTestLLM = async (name: string) => {
    try {
      const res = await api.config.llmTest(name)
      toast.success(res.message || "Test succeeded")
    } catch (e: any) {
      toast.error(e.message || "Test failed")
    }
  }

  const handleAddEmb = async () => {
    await api.config.embCreate(newEmb)
    toast.success("Embedding config added")
    setEmbDialogOpen(false)
    await loadConfigs()
  }

  const handleTestEmb = async (name: string) => {
    try {
      const res = await api.config.embTest(name)
      toast.success(res.message || "Test succeeded")
    } catch (e: any) {
      toast.error(e.message || "Test failed")
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    if (deleteTarget.type === "llm") {
      await api.config.llmDelete(deleteTarget.name)
    } else {
      await api.config.embDelete(deleteTarget.name)
    }
    toast.success("Config deleted")
    setDeleteTarget(null)
    await loadConfigs()
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-8 text-3xl font-bold">API Settings</h1>

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
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add LLM
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add LLM config</DialogTitle>
                </DialogHeader>
                <div className="space-y-3">
                  <ConfigInput label="Name" value={newLLM.name} onChange={(name) => setNewLLM({ ...newLLM, name })} />
                  <ConfigInput label="API Key" type="password" value={newLLM.api_key} onChange={(api_key) => setNewLLM({ ...newLLM, api_key })} />
                  <ConfigInput label="Base URL" value={newLLM.base_url} onChange={(base_url) => setNewLLM({ ...newLLM, base_url })} />
                  <ConfigInput label="Model" value={newLLM.model_name} onChange={(model_name) => setNewLLM({ ...newLLM, model_name })} />
                  <FormatSelect value={newLLM.interface_format} onChange={(interface_format) => setNewLLM({ ...newLLM, interface_format })} />
                  <UsageSelect value={newLLM.usage} onChange={(usage) => setNewLLM({ ...newLLM, usage })} />
                  <Button onClick={handleAddLLM} className="w-full" disabled={!newLLM.name || !newLLM.api_key}>
                    Add
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {Object.keys(llmConfigs).length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">No LLM configs yet.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(llmConfigs).map(([name, conf]) => (
                <Card key={name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-base">{name}</CardTitle>
                      <div className="flex items-center gap-1.5">
                        <Badge variant="outline" className="text-xs">{USAGE_OPTIONS.find(u => u.value === conf.usage)?.label || "通用"}</Badge>
                        <Badge>{conf.interface_format || "Unknown"}</Badge>
                      </div>
                    </div>
                    <CardDescription className="truncate">{conf.model_name} - {conf.base_url}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <span>Key: {conf.api_key_masked || "-"}</span>
                      <span>Temp: {conf.temperature ?? "-"}</span>
                      <span>Max Tokens: {conf.max_tokens ?? "-"}</span>
                    </div>
                    <ConfigActions onTest={() => handleTestLLM(name)} onDelete={() => setDeleteTarget({ type: "llm", name })} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="embedding">
          <div className="mb-4 flex justify-end">
            <Dialog open={embDialogOpen} onOpenChange={setEmbDialogOpen}>
              <DialogTrigger>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Embedding
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Embedding config</DialogTitle>
                </DialogHeader>
                <div className="space-y-3">
                  <ConfigInput label="Name" value={newEmb.name} onChange={(name) => setNewEmb({ ...newEmb, name })} />
                  <ConfigInput label="API Key" type="password" value={newEmb.api_key} onChange={(api_key) => setNewEmb({ ...newEmb, api_key })} />
                  <ConfigInput label="Base URL" value={newEmb.base_url} onChange={(base_url) => setNewEmb({ ...newEmb, base_url })} />
                  <ConfigInput label="Model" value={newEmb.model_name} onChange={(model_name) => setNewEmb({ ...newEmb, model_name })} />
                  <FormatSelect value={newEmb.interface_format} onChange={(interface_format) => setNewEmb({ ...newEmb, interface_format })} />
                  <Button onClick={handleAddEmb} className="w-full" disabled={!newEmb.name || !newEmb.api_key}>
                    Add
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {Object.keys(embConfigs).length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">No Embedding configs yet.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(embConfigs).map(([name, conf]) => (
                <Card key={name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-base">{name}</CardTitle>
                      <Badge>{conf.interface_format || "Unknown"}</Badge>
                    </div>
                    <CardDescription className="truncate">{conf.model_name} - {conf.base_url}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-2 text-sm text-muted-foreground">
                      Key: {conf.api_key_masked || "-"} / Top-K: {conf.retrieval_k ?? "-"}
                    </div>
                    <ConfigActions onTest={() => handleTestEmb(name)} onDelete={() => setDeleteTarget({ type: "emb", name })} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete config</DialogTitle>
            <DialogDescription>
              Delete config {deleteTarget?.name}. The server may reject deleting the only remaining config.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
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
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}

function FormatSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div>
      <Label>Interface format</Label>
      <Select value={value} onValueChange={(v) => v && onChange(v)}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {INTERFACE_FORMATS.map((format) => (
            <SelectItem key={format} value={format}>{format}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function UsageSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div>
      <Label>用途 (usage)</Label>
      <Select value={value} onValueChange={(v) => v && onChange(v)}>
        <SelectTrigger>
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

function ConfigActions({ onTest, onDelete }: { onTest: () => void; onDelete: () => void }) {
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="outline" onClick={onTest}>
        <TestTube className="mr-1 h-3 w-3" />
        Test
      </Button>
      <Button size="sm" variant="ghost" onClick={onDelete}>
        <Trash2 className="mr-1 h-3 w-3" />
        Delete
      </Button>
    </div>
  )
}
