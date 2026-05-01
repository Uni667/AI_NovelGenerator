"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { Plus, Trash2, TestTube, Cpu, Key } from "lucide-react"

const INTERFACE_FORMATS = ["OpenAI", "Azure OpenAI", "Ollama", "DeepSeek", "Gemini", "ML Studio", "硅基流动", "火山引擎", "阿里云百炼"]

export default function SettingsPage() {
  const [llmConfigs, setLLMConfigs] = useState<Record<string, any>>({})
  const [embConfigs, setEmbConfigs] = useState<Record<string, any>>({})
  const [newLLM, setNewLLM] = useState({ name: "", api_key: "", base_url: "https://api.openai.com/v1", model_name: "gpt-4o-mini", temperature: 0.7, max_tokens: 8192, timeout: 600, interface_format: "OpenAI" })
  const [newEmb, setNewEmb] = useState({ name: "", api_key: "", base_url: "https://api.openai.com/v1", model_name: "text-embedding-ada-002", retrieval_k: 4, interface_format: "OpenAI" })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [embDialogOpen, setEmbDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ type: "llm" | "emb"; name: string } | null>(null)

  const loadConfigs = async () => {
    const llm = await api.config.llmList()
    const emb = await api.config.embList()
    setLLMConfigs(llm)
    setEmbConfigs(emb)
  }

  useEffect(() => { loadConfigs() }, [])

  const handleAddLLM = async () => {
    await api.config.llmCreate(newLLM)
    toast.success("LLM 配置已添加")
    setDialogOpen(false)
    loadConfigs()
  }

  const handleTestLLM = async (name: string) => {
    try {
      const res = await api.config.llmTest(name)
      toast.success(res.message)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDeleteLLM = async () => {
    if (!deleteTarget) return
    await api.config.llmDelete(deleteTarget.name)
    toast.success("已删除")
    setDeleteTarget(null)
    loadConfigs()
  }

  const handleAddEmb = async () => {
    await api.config.embCreate(newEmb)
    toast.success("Embedding 配置已添加")
    setEmbDialogOpen(false)
    loadConfigs()
  }

  const handleTestEmb = async (name: string) => {
    try {
      const res = await api.config.embTest(name)
      toast.success(res.message)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDeleteEmb = async () => {
    if (!deleteTarget) return
    await api.config.embDelete(deleteTarget.name)
    toast.success("已删除")
    setDeleteTarget(null)
    loadConfigs()
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">我的 API 配置</h1>

      <Tabs defaultValue="llm">
        <TabsList className="mb-6">
          <TabsTrigger value="llm"><Cpu className="h-4 w-4 mr-2" />LLM 配置</TabsTrigger>
          <TabsTrigger value="embedding"><Key className="h-4 w-4 mr-2" />Embedding 配置</TabsTrigger>
        </TabsList>

        <TabsContent value="llm">
          <div className="flex justify-end mb-4">
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger>
                <Button><Plus className="h-4 w-4 mr-2" />添加 LLM</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>添加 LLM 配置</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <div><Label>配置名称</Label><Input value={newLLM.name} onChange={e => setNewLLM({ ...newLLM, name: e.target.value })} placeholder="例如：DeepSeek V3" /></div>
                  <div><Label>API Key</Label><Input type="password" value={newLLM.api_key} onChange={e => setNewLLM({ ...newLLM, api_key: e.target.value })} /></div>
                  <div><Label>Base URL</Label><Input value={newLLM.base_url} onChange={e => setNewLLM({ ...newLLM, base_url: e.target.value })} /></div>
                  <div><Label>模型名称</Label><Input value={newLLM.model_name} onChange={e => setNewLLM({ ...newLLM, model_name: e.target.value })} /></div>
                  <div><Label>接口格式</Label>
                    <Select value={newLLM.interface_format} onValueChange={(v) => v && setNewLLM({ ...newLLM, interface_format: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>{INTERFACE_FORMATS.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleAddLLM} className="w-full" disabled={!newLLM.name || !newLLM.api_key}>添加</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {Object.keys(llmConfigs).length === 0 ? (
            <p className="text-center text-muted-foreground py-8">暂无 LLM 配置，点击上方按钮添加</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(llmConfigs).map(([name, conf]: [string, any]) => (
                <Card key={name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{name}</CardTitle>
                      <Badge>{conf.interface_format}</Badge>
                    </div>
                    <CardDescription className="truncate">{conf.model_name} · {conf.base_url}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2 flex-wrap">
                      <span>密钥: {conf.api_key_masked}</span>
                      <span>·</span>
                      <span>温度: {conf.temperature}</span>
                      <span>·</span>
                      <span>Max Tokens: {conf.max_tokens}</span>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => handleTestLLM(name)}>
                        <TestTube className="h-3 w-3 mr-1" />测试
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setDeleteTarget({ type: "llm", name })}>
                        <Trash2 className="h-3 w-3 mr-1" />删除
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="embedding">
          <div className="flex justify-end mb-4">
            <Dialog open={embDialogOpen} onOpenChange={setEmbDialogOpen}>
              <DialogTrigger>
                <Button><Plus className="h-4 w-4 mr-2" />添加 Embedding</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>添加 Embedding 配置</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <div><Label>配置名称</Label><Input value={newEmb.name} onChange={e => setNewEmb({ ...newEmb, name: e.target.value })} /></div>
                  <div><Label>API Key</Label><Input type="password" value={newEmb.api_key} onChange={e => setNewEmb({ ...newEmb, api_key: e.target.value })} /></div>
                  <div><Label>Base URL</Label><Input value={newEmb.base_url} onChange={e => setNewEmb({ ...newEmb, base_url: e.target.value })} /></div>
                  <div><Label>模型名称</Label><Input value={newEmb.model_name} onChange={e => setNewEmb({ ...newEmb, model_name: e.target.value })} /></div>
                  <Button onClick={handleAddEmb} className="w-full" disabled={!newEmb.name}>添加</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {Object.keys(embConfigs).length === 0 ? (
            <p className="text-center text-muted-foreground py-8">暂无 Embedding 配置，点击上方按钮添加</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(embConfigs).map(([name, conf]: [string, any]) => (
                <Card key={name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{name}</CardTitle>
                      <Badge>{conf.interface_format}</Badge>
                    </div>
                    <CardDescription className="truncate">{conf.model_name} · {conf.base_url}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-muted-foreground mb-2">
                      密钥: {conf.api_key_masked} · Top-K: {conf.retrieval_k}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => handleTestEmb(name)}>
                        <TestTube className="h-3 w-3 mr-1" />测试
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setDeleteTarget({ type: "emb", name })}>
                        <Trash2 className="h-3 w-3 mr-1" />删除
                      </Button>
                    </div>
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
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              将删除配置 "{deleteTarget?.name}"。如果这是唯一的配置，可能无法删除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteTarget?.type === "llm" ? handleDeleteLLM() : handleDeleteEmb()}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
