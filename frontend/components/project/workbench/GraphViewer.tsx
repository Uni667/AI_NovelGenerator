"use client"

import React, { useEffect, useRef, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { useProjectContext } from "../ProjectContext"
import { Loader2, RefreshCcw, Search, X, Link as LinkIcon, Plus, Trash2, Maximize2, Play, Pause, AlertCircle } from "lucide-react"
import ForceGraph2D from "react-force-graph-2d"
import { useTheme } from "next-themes"
import { Badge } from "@/components/ui/badge"

interface GraphData {
  nodes: { id: string; group: string }[]
  links: { source: string; target: string; label: string }[]
}

// 兼容性圆角矩形绘制函数
const drawRoundRect = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) => {
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, w, h, r)
  } else {
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.arcTo(x + w, y, x + w, y + h, r)
    ctx.arcTo(x + w, y + h, x, y + h, r)
    ctx.arcTo(x, y + h, x, y, r)
    ctx.arcTo(x, y, x + w, y, r)
    ctx.closePath()
  }
}

export function GraphViewer() {
  const { projectId } = useProjectContext()
  const { theme, resolvedTheme } = useTheme()
  const [data, setData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)

  const [selectedNode, setSelectedNode] = useState<{ id: string; group: string } | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  // 状态开关与过滤器
  const [visibleGroups, setVisibleGroups] = useState<Set<string>>(
    new Set(["character", "item", "location", "faction", "unknown"])
  )
  const [showEdgeLabels, setShowEdgeLabels] = useState(true)
  const [isPhysicsActive, setIsPhysicsActive] = useState(true)

  // 添加节点弹窗状态
  const [isAddNodeOpen, setIsAddNodeOpen] = useState(false)
  const [newNodeId, setNewNodeId] = useState("")
  const [newNodeGroup, setNewNodeGroup] = useState("character")

  // 添加关系弹窗状态
  const [isAddRelationOpen, setIsAddRelationOpen] = useState(false)
  const [newRelSource, setNewRelSource] = useState("")
  const [newRelTarget, setNewRelTarget] = useState("")
  const [newRelLabel, setNewRelLabel] = useState("")

  const [submitting, setSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const isDark = resolvedTheme === "dark" || theme === "dark"

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      setSelectedNode(null)
      const graphData = await api.knowledge.getGraph(projectId)
      setData(graphData as unknown as GraphData)
    } catch (err: any) {
      setError(err.message || "无法加载知识图谱")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  // 根据分类过滤的图谱节点和连线
  const filteredData = React.useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const nodes = data.nodes.filter((n) => visibleGroups.has(n.group))
    const nodeIds = new Set(nodes.map((n) => n.id))
    const links = data.links.filter((l) => {
      const sId = typeof l.source === "object" ? (l.source as any).id : l.source
      const tId = typeof l.target === "object" ? (l.target as any).id : l.target
      return nodeIds.has(sId) && nodeIds.has(tId)
    })
    return { nodes, links }
  }, [data, visibleGroups])

  // 计算一阶邻居
  const neighbors = React.useMemo(() => {
    if (!selectedNode || !data) return new Set<string>()
    const set = new Set<string>()
    set.add(selectedNode.id)
    data.links.forEach((link) => {
      const sId = typeof link.source === "object" ? (link.source as any).id : link.source
      const tId = typeof link.target === "object" ? (link.target as any).id : link.target
      if (sId === selectedNode.id) {
        set.add(tId)
      } else if (tId === selectedNode.id) {
        set.add(sId)
      }
    })
    return set
  }, [selectedNode, data])

  // 计算关联连线
  const highlightLinks = React.useMemo(() => {
    if (!selectedNode || !data) return new Set<any>()
    const set = new Set<any>()
    data.links.forEach((link) => {
      const sId = typeof link.source === "object" ? (link.source as any).id : link.source
      const tId = typeof link.target === "object" ? (link.target as any).id : link.target
      if (sId === selectedNode.id || tId === selectedNode.id) {
        set.add(link)
      }
    })
    return set
  }, [selectedNode, data])

  // 节点详情面板的关系三元组
  const nodeRelations = React.useMemo(() => {
    if (!selectedNode || !data) return []
    return data.links
      .filter((link) => {
        const sId = typeof link.source === "object" ? (link.source as any).id : link.source
        const tId = typeof link.target === "object" ? (link.target as any).id : link.target
        return sId === selectedNode.id || tId === selectedNode.id
      })
      .map((link) => {
        const sId = typeof link.source === "object" ? (link.source as any).id : link.source
        const tId = typeof link.target === "object" ? (link.target as any).id : link.target
        const sourceNode = data.nodes.find((n) => n.id === sId)
        const targetNode = data.nodes.find((n) => n.id === tId)
        return {
          source: sId,
          sourceGroup: sourceNode?.group || "other",
          target: tId,
          targetGroup: targetNode?.group || "other",
          label: link.label,
        }
      })
  }, [selectedNode, data])

  // 监听物理引擎开关
  useEffect(() => {
    if (graphRef.current) {
      if (isPhysicsActive) {
        graphRef.current.resumeAnimation()
        graphRef.current.d3ReheatSimulation()
      } else {
        graphRef.current.pauseAnimation()
      }
    }
  }, [isPhysicsActive])

  // 平滑聚焦节点
  const focusOnNode = useCallback(
    (nodeId: string) => {
      if (!data || !graphRef.current) return
      const node = data.nodes.find((n) => n.id === nodeId)
      if (node) {
        const n = node as any
        setTimeout(() => {
          if (typeof n.x === "number" && typeof n.y === "number") {
            graphRef.current.centerAt(n.x, n.y, 800)
            graphRef.current.zoom(2.0, 800)
          }
        }, 50)
      }
    },
    [data]
  )

  const selectAndFocusNode = useCallback(
    (nodeId: string, group: string) => {
      setSelectedNode({ id: nodeId, group })
      focusOnNode(nodeId)
    },
    [focusOnNode]
  )

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    updateDimensions()
    window.addEventListener("resize", updateDimensions)
    return () => window.removeEventListener("resize", updateDimensions)
  }, [])

  const getNodeColor = (group: string) => {
    switch (group) {
      case "character":
        return isDark ? "#34d399" : "#059669" // emerald
      case "item":
        return isDark ? "#facc15" : "#ca8a04" // yellow
      case "location":
        return isDark ? "#60a5fa" : "#2563eb" // blue
      case "faction":
        return isDark ? "#f472b6" : "#db2777" // pink
      default:
        return isDark ? "#a1a1aa" : "#71717a" // zinc
    }
  }

  const getGroupNameZh = (group: string) => {
    switch (group) {
      case "character":
        return "角色"
      case "item":
        return "物品"
      case "location":
        return "地点"
      case "faction":
        return "势力"
      default:
        return "未知"
    }
  }

  // 切换类型过滤
  const toggleGroup = (group: string) => {
    setVisibleGroups((prev) => {
      const next = new Set(prev)
      if (next.has(group)) {
        next.delete(group)
      } else {
        next.add(group)
      }
      return next
    })
  }

  // CRUD 事件处理器
  const handleAddNode = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newNodeId.trim()) return
    try {
      setSubmitting(true)
      setActionError(null)
      await api.knowledge.addNode(projectId, { id: newNodeId.trim(), group: newNodeGroup })
      setNewNodeId("")
      setIsAddNodeOpen(false)
      await fetchGraph()
    } catch (err: any) {
      setActionError(err.message || "添加节点失败")
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteNode = async (nodeId: string) => {
    if (!confirm(`确认要删除实体“${nodeId}”吗？此操作会同时删除该实体的所有关联关系。`)) return
    try {
      setSubmitting(true)
      setActionError(null)
      await api.knowledge.deleteNode(projectId, nodeId)
      setSelectedNode(null)
      await fetchGraph()
    } catch (err: any) {
      alert(err.message || "删除节点失败")
    } finally {
      setSubmitting(false)
    }
  }

  const handleAddRelation = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newRelSource.trim() || !newRelTarget.trim() || !newRelLabel.trim()) return
    try {
      setSubmitting(true)
      setActionError(null)
      await api.knowledge.addRelation(projectId, {
        source: newRelSource.trim(),
        target: newRelTarget.trim(),
        label: newRelLabel.trim(),
      })
      setNewRelSource("")
      setNewRelTarget("")
      setNewRelLabel("")
      setIsAddRelationOpen(false)
      await fetchGraph()
    } catch (err: any) {
      setActionError(err.message || "添加关系失败")
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteRelation = async (source: string, target: string) => {
    if (!confirm(`确认要删除“${source}”与“${target}”之间的关系吗？`)) return
    try {
      setSubmitting(true)
      await api.knowledge.deleteRelation(projectId, source, target)
      await fetchGraph()
    } catch (err: any) {
      alert(err.message || "删除关系失败")
    } finally {
      setSubmitting(false)
    }
  }

  const handleResetZoom = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400)
    }
  }

  if (loading && !data) {
    return (
      <div className="flex h-full min-h-[400px] w-full items-center justify-center bg-background/50 rounded-lg border border-border">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">正在加载图谱记忆...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex h-full min-h-[400px] w-full flex-col items-center justify-center gap-4 bg-background/50 rounded-lg border border-border">
        <p className="text-sm text-destructive">{error}</p>
        <button
          onClick={fetchGraph}
          className="flex items-center gap-2 text-sm hover:text-primary transition-colors px-3 py-1.5 rounded-lg border border-border bg-background"
        >
          <RefreshCcw className="h-4 w-4" /> 重试
        </button>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="relative h-full min-h-[600px] w-full rounded-xl overflow-hidden border border-border/80 bg-slate-950/20 backdrop-blur-md shadow-2xl flex flex-row"
    >
      {/* 左侧图谱区 */}
      <div className="flex-1 h-full relative min-w-0">
        {/* 顶部悬浮控制栏 */}
        <div className="absolute top-4 left-4 right-4 z-10 flex flex-wrap gap-2 items-center justify-between pointer-events-none">
          {/* 左侧搜索与图例 */}
          <div className="flex flex-col gap-2 pointer-events-auto max-w-xs md:max-w-md">
            {/* 实体搜索 */}
            <div className="bg-slate-900/90 backdrop-blur-md border border-white/10 px-3 py-2 rounded-xl shadow-xl flex items-center gap-2 w-64">
              <Search className="h-4 w-4 text-slate-400 shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索节点实体..."
                className="w-full text-xs bg-transparent border-0 focus:outline-none focus:ring-0 text-slate-200 placeholder:text-slate-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="text-slate-400 hover:text-slate-200 shrink-0"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {/* 实体类型过滤标签 */}
            <div className="bg-slate-900/90 backdrop-blur-md border border-white/10 p-3 rounded-xl shadow-xl flex flex-col gap-2 w-64">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                实体类型过滤
              </div>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                {[
                  { key: "character", color: "emerald", label: "角色", bg: "bg-emerald-500" },
                  { key: "item", color: "yellow", label: "物品", bg: "bg-yellow-500" },
                  { key: "location", color: "blue", label: "地点", bg: "bg-blue-500" },
                  { key: "faction", color: "pink", label: "势力", bg: "bg-pink-500" },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => toggleGroup(item.key)}
                    className={`flex items-center gap-2 px-2 py-1 rounded-md border text-left transition-all ${
                      visibleGroups.has(item.key)
                        ? "bg-slate-800/80 border-slate-700 text-slate-200"
                        : "bg-slate-950/20 border-transparent text-slate-500"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${item.bg} shrink-0`} />
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 右侧全局操作面板 */}
          <div className="flex gap-2 pointer-events-auto">
            {/* 物理引擎 */}
            <button
              onClick={() => setIsPhysicsActive(!isPhysicsActive)}
              className={`p-2.5 rounded-xl border border-white/10 shadow-xl backdrop-blur transition-all ${
                isPhysicsActive
                  ? "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                  : "bg-slate-900/95 text-slate-400 hover:bg-slate-800"
              }`}
              title={isPhysicsActive ? "暂停物理引擎" : "启用物理引擎"}
            >
              {isPhysicsActive ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </button>

            {/* 显示连线文本 */}
            <button
              onClick={() => setShowEdgeLabels(!showEdgeLabels)}
              className={`p-2.5 rounded-xl border border-white/10 shadow-xl backdrop-blur transition-all ${
                showEdgeLabels
                  ? "bg-sky-500/10 text-sky-400 hover:bg-sky-500/20"
                  : "bg-slate-900/95 text-slate-400 hover:bg-slate-800"
              }`}
              title="显示关系名称"
            >
              <LinkIcon className="h-4 w-4" />
            </button>

            {/* 自适应居中 */}
            <button
              onClick={handleResetZoom}
              className="p-2.5 bg-slate-900/95 text-slate-400 hover:text-slate-200 border border-white/10 rounded-xl shadow-xl hover:bg-slate-800 transition-all"
              title="自适应居中"
            >
              <Maximize2 className="h-4 w-4" />
            </button>

            {/* 添加数据 */}
            <button
              onClick={() => setIsAddNodeOpen(true)}
              className="px-3 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl shadow-xl flex items-center gap-1.5 text-xs font-semibold transition-all"
            >
              <Plus className="h-3.5 w-3.5" /> 节点
            </button>

            <button
              onClick={() => setIsAddRelationOpen(true)}
              className="px-3 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl shadow-xl flex items-center gap-1.5 text-xs font-semibold transition-all"
            >
              <Plus className="h-3.5 w-3.5" /> 关系
            </button>

            {/* 刷新 */}
            <button
              onClick={fetchGraph}
              className="p-2.5 bg-slate-900/95 text-slate-400 hover:text-slate-200 border border-white/10 rounded-xl shadow-xl hover:bg-slate-800 transition-all"
              title="刷新图谱"
            >
              <RefreshCcw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* 关系图画布组件 */}
        <ForceGraph2D
          ref={graphRef}
          width={selectedNode ? dimensions.width - 320 : dimensions.width}
          height={dimensions.height}
          graphData={filteredData}
          nodeColor={(node: any) => getNodeColor(node.group)}
          nodeLabel="id"
          nodeRelSize={6}
          linkColor={() => (isDark ? "rgba(255,255,255,0.18)" : "rgba(15, 23, 42, 0.15)")}
          linkWidth={(link: any) => {
            if (selectedNode && highlightLinks.has(link)) {
              return 3.0
            }
            return 1.2
          }}
          linkDirectionalArrowLength={4.0}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.25}
          linkLabel="label"
          backgroundColor={isDark ? "transparent" : "#f8fafc"}
          onNodeClick={(node: any) => {
            if (selectedNode && selectedNode.id === node.id) {
              setSelectedNode(null)
            } else {
              setSelectedNode({ id: node.id, group: node.group })
              focusOnNode(node.id)
            }
          }}
          onBackgroundClick={() => {
            setSelectedNode(null)
          }}
          // 高清药丸式节点胶囊卡片
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            const label = node.id
            const fontSize = 11 / globalScale
            ctx.font = `${fontSize}px Inter, -apple-system, sans-serif`
            const textWidth = ctx.measureText(label).width

            const paddingX = 8 / globalScale
            const paddingY = 4 / globalScale
            const dotSize = 3.5 / globalScale
            const dotPadding = 5 / globalScale

            const pillHeight = fontSize + paddingY * 2
            const pillWidth = textWidth + paddingX * 2 + dotSize + dotPadding

            let alpha = 1.0
            const hasSelection = selectedNode !== null
            const hasSearch = searchQuery.trim() !== ""

            if (hasSelection) {
              const isNeighbor = neighbors.has(node.id)
              if (!isNeighbor) {
                alpha = 0.15
              }
            }
            if (hasSearch) {
              const matches = node.id.toLowerCase().includes(searchQuery.toLowerCase())
              if (!matches) {
                alpha = 0.15
              }
            }

            ctx.save()
            ctx.globalAlpha = alpha

            // Hover/选中态外层高光环
            if (selectedNode && selectedNode.id === node.id) {
              ctx.shadowBlur = 10 / globalScale
              ctx.shadowColor = getNodeColor(node.group)
              ctx.strokeStyle = getNodeColor(node.group)
              ctx.lineWidth = 2.0 / globalScale
              ctx.beginPath()
              drawRoundRect(
                ctx,
                node.x - pillWidth / 2 - 2 / globalScale,
                node.y - pillHeight / 2 - 2 / globalScale,
                pillWidth + 4 / globalScale,
                pillHeight + 4 / globalScale,
                pillHeight / 2 + 2 / globalScale
              )
              ctx.stroke()
            }

            // 绘制胶囊背景板
            ctx.fillStyle = isDark ? "rgba(15, 23, 42, 0.92)" : "rgba(255, 255, 255, 0.95)"
            ctx.strokeStyle = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(15, 23, 42, 0.08)"
            ctx.lineWidth = 1.0 / globalScale
            ctx.beginPath()
            drawRoundRect(
              ctx,
              node.x - pillWidth / 2,
              node.y - pillHeight / 2,
              pillWidth,
              pillHeight,
              pillHeight / 2
            )
            ctx.fill()
            ctx.stroke()

            // 绘制类别小圆点
            ctx.fillStyle = getNodeColor(node.group)
            ctx.beginPath()
            ctx.arc(
              node.x - pillWidth / 2 + paddingX + dotSize / 2,
              node.y,
              dotSize,
              0,
              2 * Math.PI
            )
            ctx.fill()

            // 绘制文字
            ctx.textAlign = "left"
            ctx.textBaseline = "middle"
            ctx.fillStyle = isDark ? "#f8fafc" : "#0f172a"
            ctx.fillText(
              label,
              node.x - pillWidth / 2 + paddingX + dotSize + dotPadding,
              node.y
            )

            ctx.restore()
            node.__bckgDimensions = [pillWidth, pillHeight]
          }}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            ctx.fillStyle = color
            const bckgDimensions = node.__bckgDimensions
            if (bckgDimensions) {
              ctx.fillRect(
                node.x - bckgDimensions[0] / 2,
                node.y - bckgDimensions[1] / 2,
                bckgDimensions[0],
                bckgDimensions[1]
              )
            }
          }}
          // 绘制连线文字
          linkCanvasObjectMode={() => (showEdgeLabels ? "after" : undefined)}
          linkCanvasObject={(link: any, ctx, globalScale) => {
            const start = link.source
            const end = link.target
            if (typeof start !== "object" || typeof end !== "object") return

            // 计算中心位置
            const x = start.x + (end.x - start.x) * 0.5
            const y = start.y + (end.y - start.y) * 0.5
            const label = link.label || ""
            if (!label) return

            const fontSize = 9 / globalScale
            ctx.font = `${fontSize}px Inter, sans-serif`
            const textWidth = ctx.measureText(label).width

            ctx.save()
            const dy = end.y - start.y
            const dx = end.x - start.x
            let angle = Math.atan2(dy, dx)
            if (angle > Math.PI / 2) angle -= Math.PI
            if (angle < -Math.PI / 2) angle += Math.PI

            ctx.translate(x, y)
            ctx.rotate(angle)

            // 文字白底/黑底框
            ctx.fillStyle = isDark ? "rgba(9, 9, 11, 0.9)" : "rgba(255, 255, 255, 0.9)"
            ctx.fillRect(
              -textWidth / 2 - 3 / globalScale,
              -fontSize / 2 - 2 / globalScale,
              textWidth + 6 / globalScale,
              fontSize + 4 / globalScale
            )

            // 绘制文字
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillStyle = isDark ? "rgba(161, 161, 170, 0.8)" : "rgba(63, 63, 70, 0.8)"
            ctx.fillText(label, 0, 0)
            ctx.restore()
          }}
        />
      </div>

      {/* 右侧节点详情面板 */}
      {selectedNode && (
        <div className="w-[320px] shrink-0 border-l border-border/80 bg-slate-900/60 backdrop-blur-xl p-5 flex flex-col gap-4 animate-in slide-in-from-right duration-200 overflow-y-auto z-20">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <h3 className="font-extrabold text-base tracking-tight truncate flex-1 text-slate-100">
              {selectedNode.id}
            </h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-slate-200 rounded-lg p-1.5 hover:bg-slate-800"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 flex flex-col gap-4 min-h-0">
            {/* 实体类别 */}
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                实体类型
              </span>
              <div>
                <Badge
                  variant="outline"
                  className="px-2.5 py-1 text-xs font-semibold"
                  style={{
                    color: getNodeColor(selectedNode.group),
                    borderColor: `${getNodeColor(selectedNode.group)}30`,
                    backgroundColor: `${getNodeColor(selectedNode.group)}10`,
                  }}
                >
                  {getGroupNameZh(selectedNode.group)} ({selectedNode.group})
                </Badge>
              </div>
            </div>

            {/* 关联关系 */}
            <div className="space-y-2 flex-1 flex flex-col min-h-0">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
                <LinkIcon className="h-3 w-3" />
                三元组关系 ({nodeRelations.length})
              </span>

              {nodeRelations.length === 0 ? (
                <p className="text-xs text-slate-400 italic">暂无直接关联的其他节点。</p>
              ) : (
                <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1 flex-1">
                  {nodeRelations.map((rel, idx) => {
                    const isSourceSelf = rel.source === selectedNode.id
                    const neighborId = isSourceSelf ? rel.target : rel.source
                    const neighborGroup = isSourceSelf ? rel.targetGroup : rel.sourceGroup

                    return (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 transition-all flex items-center justify-between gap-2"
                      >
                        <div className="flex flex-wrap items-center gap-1 leading-relaxed text-xs">
                          <span
                            onClick={() =>
                              !isSourceSelf && selectAndFocusNode(rel.source, rel.sourceGroup)
                            }
                            className={`font-semibold cursor-pointer ${
                              isSourceSelf
                                ? "text-slate-100"
                                : "hover:text-primary hover:underline"
                            }`}
                            style={!isSourceSelf ? { color: getNodeColor(rel.sourceGroup) } : {}}
                          >
                            {rel.source}
                          </span>
                          <span className="text-slate-400 font-mono text-[10px] px-1 bg-slate-800 rounded border border-white/5">
                            {rel.label}
                          </span>
                          <span
                            onClick={() =>
                              isSourceSelf && selectAndFocusNode(rel.target, rel.targetGroup)
                            }
                            className={`font-semibold cursor-pointer ${
                              !isSourceSelf
                                ? "text-slate-100"
                                : "hover:text-primary hover:underline"
                            }`}
                            style={isSourceSelf ? { color: getNodeColor(rel.targetGroup) } : {}}
                          >
                            {rel.target}
                          </span>
                        </div>

                        {/* 删除关系图标 */}
                        <button
                          onClick={() => handleDeleteRelation(rel.source, rel.target)}
                          className="p-1 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded transition-all shrink-0"
                          title="删除此关系"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* 删除实体按钮 */}
            <div className="pt-2 border-t border-border/60">
              <button
                onClick={() => handleDeleteNode(selectedNode.id)}
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 hover:text-red-300 disabled:opacity-50 text-xs font-semibold rounded-xl transition-all"
              >
                <Trash2 className="h-4 w-4" /> 删除实体节点
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== Modal Overlay: Add Node ==================== */}
      {isAddNodeOpen && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-sm p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
              <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <Plus className="h-4 w-4 text-emerald-400" /> 手动创建节点
              </h4>
              <button
                onClick={() => setIsAddNodeOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddNode} className="space-y-4">
              {actionError && (
                <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {actionError}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  节点名称 / 实体名
                </label>
                <input
                  type="text"
                  required
                  value={newNodeId}
                  onChange={(e) => setNewNodeId(e.target.value)}
                  placeholder="如：黑金古刀、林澜"
                  className="w-full text-xs px-3 py-2 bg-slate-950 border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  节点类别
                </label>
                <select
                  value={newNodeGroup}
                  onChange={(e) => setNewNodeGroup(e.target.value)}
                  className="w-full text-xs px-3 py-2 bg-slate-950 border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200"
                >
                  <option value="character">角色</option>
                  <option value="item">物品</option>
                  <option value="location">地点</option>
                  <option value="faction">势力</option>
                  <option value="unknown">未知/其他</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddNodeOpen(false)}
                  className="flex-1 px-4 py-2 border border-white/10 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-semibold rounded-xl transition-all"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition-all"
                >
                  {submitting ? "创建中..." : "确认创建"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== Modal Overlay: Add Relation ==================== */}
      {isAddRelationOpen && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-sm p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
              <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <Plus className="h-4 w-4 text-indigo-400" /> 手动创建三元组关系
              </h4>
              <button
                onClick={() => setIsAddRelationOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddRelation} className="space-y-4">
              {actionError && (
                <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {actionError}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  源节点 (实体 A)
                </label>
                <input
                  type="text"
                  required
                  value={newRelSource}
                  onChange={(e) => setNewRelSource(e.target.value)}
                  placeholder="如：林澜"
                  className="w-full text-xs px-3 py-2 bg-slate-950 border border-white/10 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-200"
                  list="node-suggestions"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  关系名称 (Label)
                </label>
                <input
                  type="text"
                  required
                  value={newRelLabel}
                  onChange={(e) => setNewRelLabel(e.target.value)}
                  placeholder="如：拥有、位于、敌对"
                  className="w-full text-xs px-3 py-2 bg-slate-950 border border-white/10 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-200"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  目标节点 (实体 B)
                </label>
                <input
                  type="text"
                  required
                  value={newRelTarget}
                  onChange={(e) => setNewRelTarget(e.target.value)}
                  placeholder="如：黑金古刀"
                  className="w-full text-xs px-3 py-2 bg-slate-950 border border-white/10 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-200"
                  list="node-suggestions"
                />
              </div>

              {/* 实体智能联想提示 */}
              {data && (
                <datalist id="node-suggestions">
                  {data.nodes.map((n) => (
                    <option key={n.id} value={n.id} />
                  ))}
                </datalist>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddRelationOpen(false)}
                  className="flex-1 px-4 py-2 border border-white/10 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-semibold rounded-xl transition-all"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition-all"
                >
                  {submitting ? "创建中..." : "确认创建"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
