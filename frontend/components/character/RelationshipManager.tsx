"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { Plus, Trash2, Edit3, GitBranch, Info } from "lucide-react"
import type { CharacterRelationship, CharacterProfile, RelationshipGraph } from "@/lib/types"
import { RELATIONSHIP_TYPE_LABELS } from "@/lib/types"

interface Props {
  projectId: string
  characters: CharacterProfile[]
}

interface RelForm {
  character_id_a: number
  character_id_b: number
  rel_type: string
  description: string
  strength: number
  direction: string
  start_chapter: number | null
  status: string
}

const STATUS_LABELS: Record<string, string> = {
  active: "活跃", strained: "紧张", broken: "破裂", evolving: "演变中", resolved: "已化解",
}

const STATUS_COLORS: Record<string, string> = {
  active: "text-indigo-400 border-indigo-500/25 bg-indigo-500/10",
  strained: "text-orange-400 border-orange-500/25 bg-orange-500/10",
  broken: "text-red-400 border-red-500/25 bg-red-500/10",
  evolving: "text-purple-400 border-purple-500/25 bg-purple-500/10",
  resolved: "text-emerald-400 border-emerald-500/25 bg-emerald-500/10",
}

const CHARACTER_STATUS_LABELS: Record<string, string> = {
  appeared: "已出场",
  planned: "计划中",
  suggested: "AI推荐",
}

const characterStatusLabel = (status?: string) => {
  if (!status) return "已出场"
  return CHARACTER_STATUS_LABELS[status] || status
}

export default function RelationshipManager({ projectId, characters }: Props) {
  const [relationships, setRelationships] = useState<CharacterRelationship[]>([])
  const [graph, setGraph] = useState<RelationshipGraph | null>(null)
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CharacterRelationship | null>(null)
  const [hoveredNode, setHoveredNode] = useState<number | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null)

  const [form, setForm] = useState<RelForm>({
    character_id_a: 0, character_id_b: 0, rel_type: "",
    description: "", strength: 0.5, direction: "bidirectional",
    start_chapter: null, status: "active",
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rels, g] = await Promise.all([
        api.characterRelationships.list(projectId),
        api.characterRelationships.graph(projectId).catch(() => null),
      ])
      setRelationships(rels)
      setGraph(g)
    } catch (e: any) {
      toast.error(e?.message || "加载关系数据失败")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const resetForm = () => {
    setForm({
      character_id_a: 0, character_id_b: 0, rel_type: "friend",
      description: "", strength: 0.5, direction: "bidirectional",
      start_chapter: null, status: "active"
    })
    setEditing(null)
  }

  const openCreate = () => { resetForm(); setDialogOpen(true) }
  const openEdit = (rel: CharacterRelationship) => {
    setEditing(rel)
    setForm({
      character_id_a: rel.character_id_a, character_id_b: rel.character_id_b,
      rel_type: rel.rel_type, description: rel.description, strength: rel.strength,
      direction: rel.direction, start_chapter: rel.start_chapter, status: rel.status,
    })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.character_id_a || !form.character_id_b || form.character_id_a === form.character_id_b) {
      toast.error("请选择两个不同的角色"); return
    }
    try {
      if (editing) { await api.characterRelationships.update(projectId, editing.id, form) }
      else { await api.characterRelationships.create(projectId, form) }
      toast.success(editing ? "关系已更新" : "关系已创建")
      setDialogOpen(false); load()
    } catch (e: any) { toast.error(e?.message || "保存失败") }
  }

  const handleDelete = async (relId: number) => {
    if (!confirm("确定删除这条关系？")) return
    try { await api.characterRelationships.delete(projectId, relId); toast.success("已删除"); load() }
    catch (e: any) { toast.error(e?.message || "删除失败") }
  }

  const charName = (id: number) => characters.find(c => c.id === id)?.name || `#${id}`
  const update = (key: keyof RelForm, value: any) => setForm(f => ({ ...f, [key]: value } as RelForm))

  // Calculate circular layout positions for nodes
  const nodeCount = graph?.nodes.length || 0
  const width = 600
  const height = 400
  const centerX = width / 2
  const centerY = height / 2
  const radius = 135

  const nodePositions = new Map<number, { x: number; y: number }>()
  if (graph) {
    graph.nodes.forEach((node, idx) => {
      const angle = (idx * 2 * Math.PI) / nodeCount - Math.PI / 2
      const x = centerX + radius * Math.cos(angle)
      const y = centerY + radius * Math.sin(angle)
      nodePositions.set(node.id, { x, y })
    })
  }

  const getEdgeHighlightStatus = (edge: any) => {
    if (hoveredEdge === edge.id) return "hovered"
    if (hoveredNode !== null) {
      if (edge.source === hoveredNode || edge.target === hoveredNode) return "highlighted"
      return "dimmed"
    }
    if (hoveredEdge !== null) return "dimmed"
    return "default"
  }

  const getNodeHighlightStatus = (nodeId: number) => {
    if (hoveredNode === nodeId) return "hovered"
    if (hoveredNode !== null) {
      // check if this node is connected to the hovered node
      const isConnected = graph?.edges.some(
        e => (e.source === nodeId && e.target === hoveredNode) || (e.target === nodeId && e.source === hoveredNode)
      )
      return isConnected ? "highlighted" : "dimmed"
    }
    if (hoveredEdge !== null) {
      const edge = graph?.edges.find(e => e.id === hoveredEdge)
      if (edge && (edge.source === nodeId || edge.target === nodeId)) return "highlighted"
      return "dimmed"
    }
    return "default"
  }

  const getEdgeColor = (status: string) => {
    switch (status) {
      case "strained": return "stroke-orange-400"
      case "broken": return "stroke-red-500"
      case "evolving": return "stroke-purple-400"
      case "resolved": return "stroke-emerald-400"
      default: return "stroke-indigo-400"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold tracking-tight">人物关系网络</h3>
          <p className="text-xs text-muted-foreground">直观可视化的交互式人物关系图谱</p>
        </div>
        <Button onClick={openCreate} size="sm" className="shadow-md shadow-primary/20">
          <Plus className="h-4 w-4 mr-1" />新增关系
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-[350px] w-full rounded-xl" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : relationships.length === 0 ? (
        <Card className="border-dashed border-border/40 bg-muted/5">
          <CardContent className="py-12 text-center text-sm text-muted-foreground/80 leading-relaxed">
            暂无关系记录。请点击右上角「新增关系」添加。
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          {/* 左侧：SVG关系网络图 */}
          <div className="relative rounded-xl border border-border/40 bg-muted/15 flex flex-col justify-between overflow-hidden p-2 min-h-[420px] shadow-inner">
            <div className="absolute top-3 left-3 z-10 flex flex-wrap gap-1.5 items-center bg-background/80 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-border/30 text-xs">
              <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground font-semibold">
                {graph?.nodes.length || 0} 角色 · {graph?.edges.length || 0} 条关系
              </span>
            </div>
            
            <div className="absolute top-3 right-3 z-10 flex gap-2">
              <span className="text-[10px] text-muted-foreground bg-secondary/80 px-2 py-0.5 rounded border flex items-center gap-1 font-semibold">
                <Info className="h-3 w-3" /> 悬停节点以高亮其关系网
              </span>
            </div>

            <div className="flex-1 flex items-center justify-center">
              {graph && graph.nodes.length > 0 && (
                <svg
                  viewBox={`0 0 ${width} ${height}`}
                  className="w-full h-auto max-h-[380px]"
                >
                  <defs>
                    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="4" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                    {/* Directional arrow marker definitions */}
                    <marker
                      id="arrow-indigo"
                      viewBox="0 0 10 10"
                      refX="17"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" className="fill-indigo-400/80" />
                    </marker>
                    <marker
                      id="arrow-orange"
                      viewBox="0 0 10 10"
                      refX="17"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" className="fill-orange-400/80" />
                    </marker>
                    <marker
                      id="arrow-red"
                      viewBox="0 0 10 10"
                      refX="17"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" className="fill-red-500/80" />
                    </marker>
                    <marker
                      id="arrow-purple"
                      viewBox="0 0 10 10"
                      refX="17"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" className="fill-purple-400/80" />
                    </marker>
                    <marker
                      id="arrow-emerald"
                      viewBox="0 0 10 10"
                      refX="17"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" className="fill-emerald-400/80" />
                    </marker>
                  </defs>

                  {/* 绘制关系连线 */}
                  {graph.edges.map((edge) => {
                    const posA = nodePositions.get(edge.source)
                    const posB = nodePositions.get(edge.target)
                    if (!posA || !posB) return null

                    const status = getEdgeHighlightStatus(edge)
                    const opacity =
                      status === "hovered" ? 1.0 : status === "highlighted" ? 0.85 : status === "dimmed" ? 0.08 : 0.45
                    const strokeWidth =
                      status === "hovered" || status === "highlighted"
                        ? 2 + edge.strength * 4.5
                        : 1 + edge.strength * 2.5

                    // Determine arrow marker
                    let markerId = "indigo"
                    if (edge.status === "strained") markerId = "orange"
                    else if (edge.status === "broken") markerId = "red"
                    else if (edge.status === "evolving") markerId = "purple"
                    else if (edge.status === "resolved") markerId = "emerald"

                    const markerEnd = edge.direction === "a_to_b" ? `url(#arrow-${markerId})` : undefined
                    const markerStart = edge.direction === "b_to_a" ? `url(#arrow-${markerId})` : undefined

                    return (
                      <line
                        key={edge.id}
                        x1={posA.x}
                        y1={posA.y}
                        x2={posB.x}
                        y2={posB.y}
                        className={`transition-all duration-300 fill-none cursor-pointer ${getEdgeColor(
                          edge.status
                        )}`}
                        style={{ strokeOpacity: opacity, strokeWidth }}
                        markerStart={markerStart}
                        markerEnd={markerEnd}
                        onMouseEnter={() => setHoveredEdge(edge.id)}
                        onMouseLeave={() => setHoveredEdge(null)}
                      />
                    )
                  })}

                  {/* 绘制角色节点 */}
                  {graph.nodes.map((node) => {
                    const pos = nodePositions.get(node.id)
                    if (!pos) return null

                    const status = getNodeHighlightStatus(node.id)
                    const opacity = status === "dimmed" ? 0.25 : 1.0
                    const isHovered = status === "hovered"
                    const r = isHovered ? 13 : 10.5

                    let nodeStroke = "stroke-primary"
                    if (node.status === "appeared") nodeStroke = "stroke-emerald-400"
                    else if (node.status === "planned") nodeStroke = "stroke-blue-400"
                    else if (node.status === "suggested") nodeStroke = "stroke-purple-400"

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        className="cursor-pointer transition-all duration-300"
                        style={{ opacity }}
                        onMouseEnter={() => setHoveredNode(node.id)}
                        onMouseLeave={() => setHoveredNode(null)}
                      >
                        <circle
                          r={r + 3}
                          className="fill-background/45 stroke-none"
                        />
                        <circle
                          r={r}
                          className={`fill-background border ${nodeStroke} transition-all duration-200`}
                          style={{
                            strokeWidth: isHovered ? 2.5 : 1.8,
                            filter: isHovered ? "url(#glow)" : undefined,
                          }}
                        />
                        <text
                          y={r + 14}
                          className="text-[10px] font-bold fill-foreground/90 text-center select-none"
                          textAnchor="middle"
                        >
                          {node.name}
                        </text>
                      </g>
                    )
                  })}
                </svg>
              )}
            </div>

            {/* 悬停数据详情展示 */}
            <div className="h-10 border-t border-border/25 flex items-center justify-center text-xs text-muted-foreground/80 px-2.5">
              {hoveredNode !== null ? (
                <span>
                  当前选中：
                  <span className="font-bold text-foreground">
                    {graph?.nodes.find((n) => n.id === hoveredNode)?.name}
                  </span>{" "}
                  · 状态: {characterStatusLabel(graph?.nodes.find((n) => n.id === hoveredNode)?.status)}
                </span>
              ) : hoveredEdge !== null ? (
                (() => {
                  const edge = graph?.edges.find((e) => e.id === hoveredEdge)
                  if (!edge) return null
                  return (
                    <span className="flex items-center gap-1">
                      <span className="font-bold text-foreground">{edge.sourceName}</span>
                      <Badge variant="secondary" className="scale-90 text-[10px] font-medium h-5">
                        {RELATIONSHIP_TYPE_LABELS[edge.type] || edge.type}
                      </Badge>
                      <span className="text-muted-foreground/80">
                        {edge.direction === "a_to_b" ? "→" : edge.direction === "b_to_a" ? "←" : "↔"}
                      </span>
                      <span className="font-bold text-foreground mr-2">{edge.targetName}</span>
                      <span>(强度: {"★".repeat(Math.round(edge.strength * 5))} · {STATUS_LABELS[edge.status] || edge.status})</span>
                    </span>
                  )
                })()
              ) : (
                <span className="italic flex items-center gap-1"><Info className="h-3.5 w-3.5" /> 悬浮于节点或连线上查看关系描述详情</span>
              )}
            </div>
          </div>

          {/* 右侧：列表编辑与删除 */}
          <div className="flex flex-col">
            <ScrollArea className="h-[420px] rounded-xl border border-border/40 p-3 bg-card/10">
              <div className="space-y-3.5">
                {relationships.map((rel) => (
                  <Card
                    key={rel.id}
                    className={`hover:bg-accent/25 hover:border-primary/20 transition-all duration-200 ${
                      hoveredEdge === rel.id ? "border-primary bg-primary/5" : "border-border/60"
                    }`}
                  >
                    <CardContent className="p-3.5 space-y-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-bold text-sm text-foreground/90">
                              {charName(rel.character_id_a)}
                            </span>
                            <Badge variant="secondary" className="text-[10px] h-5 font-semibold bg-secondary/80 text-muted-foreground">
                              {RELATIONSHIP_TYPE_LABELS[rel.rel_type] || rel.rel_type}
                            </Badge>
                            <span className="text-muted-foreground text-xs font-semibold">
                              {rel.direction === "a_to_b" ? "→" : rel.direction === "b_to_a" ? "←" : "↔"}
                            </span>
                            <span className="font-bold text-sm text-foreground/90">
                              {charName(rel.character_id_b)}
                            </span>
                          </div>
                          {rel.description && (
                            <p className="text-xs text-muted-foreground/80 leading-relaxed font-sans line-clamp-2">
                              {rel.description}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground/90 font-medium">
                            <span className="text-amber-400">{"★".repeat(Math.round(rel.strength * 5))}</span>
                            <span className="text-muted-foreground/30">•</span>
                            <Badge variant="outline" className={`text-[10px] px-1.5 scale-95 py-0 origin-left border-none ${STATUS_COLORS[rel.status] || ""}`}>
                              {STATUS_LABELS[rel.status] || rel.status}
                            </Badge>
                            {rel.start_chapter && (
                              <>
                                <span className="text-muted-foreground/30">•</span>
                                <span>第 {rel.start_chapter} 章起</span>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEdit(rel)}
                            className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent/40 rounded-lg"
                          >
                            <Edit3 className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(rel.id)}
                            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
      )}

      {/* 关系新建/编辑对话框 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="glass-panel border-border/40 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">{editing ? "编辑关系" : "新增关系"}</DialogTitle>
            <DialogDescription className="text-xs">定义项目角色之间的情感关联与阵营变化</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">角色 A</Label>
                <Select value={String(form.character_id_a)} onValueChange={(v) => update("character_id_a", Number(v))}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue placeholder="选择角色" /></SelectTrigger>
                  <SelectContent>
                    {characters.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">角色 B</Label>
                <Select value={String(form.character_id_b)} onValueChange={(v) => update("character_id_b", Number(v))}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue placeholder="选择角色" /></SelectTrigger>
                  <SelectContent>
                    {characters.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">关系类型</Label>
                <Select value={form.rel_type} onValueChange={(v) => update("rel_type", v)}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue placeholder="选择类型" /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(RELATIONSHIP_TYPE_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">联系方向</Label>
                <Select value={form.direction} onValueChange={(v) => update("direction", v)}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bidirectional">双向联系 ↔</SelectItem>
                    <SelectItem value="a_to_b">A 单向至 B →</SelectItem>
                    <SelectItem value="b_to_a">B 单向至 A ←</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">关系详细描述</Label>
              <Textarea
                rows={3}
                value={form.description}
                onChange={(e) => update("description", e.target.value)}
                placeholder="在此描述具体的牵绊、恩怨、或隐藏利益瓜葛..."
                className="hover:border-primary/20 resize-none text-sm leading-relaxed"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">亲密强度 ({form.strength.toFixed(1)})</Label>
                <Input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={form.strength}
                  onChange={(e) => update("strength", Number(e.target.value))}
                  className="h-9 hover:border-primary/20"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">起始章节</Label>
                <Input
                  type="number"
                  value={form.start_chapter ?? ""}
                  onChange={(e) => update("start_chapter", e.target.value ? Number(e.target.value) : null)}
                  placeholder="可选"
                  className="hover:border-primary/20 text-xs"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">关系状态</Label>
                <Select value={form.status} onValueChange={(v) => update("status", v)}>
                  <SelectTrigger className="hover:border-primary/20"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(STATUS_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter className="mt-2">
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button size="sm" onClick={handleSave}>{editing ? "保存修改" : "创建关系"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
