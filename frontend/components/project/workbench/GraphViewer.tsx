"use client"

import React, { useEffect, useRef, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { useProjectContext } from "../ProjectContext"
import { Loader2, RefreshCcw, Search, X, Link as LinkIcon } from "lucide-react"
import ForceGraph2D from "react-force-graph-2d"
import { useTheme } from "next-themes"
import { Badge } from "@/components/ui/badge"

interface GraphData {
  nodes: { id: string; group: string }[]
  links: { source: string; target: string; label: string }[]
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

  const isDark = resolvedTheme === "dark" || theme === "dark"

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      setSelectedNode(null)
      const graphData = await api.knowledge.getGraph(projectId)
      setData(graphData as unknown as GraphData)
    } catch (err: any) {
      setError(err.message || "Failed to load knowledge graph")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  // 计算一阶邻居
  const neighbors = React.useMemo(() => {
    if (!selectedNode || !data) return new Set<string>()
    const set = new Set<string>()
    set.add(selectedNode.id)
    data.links.forEach(link => {
      const sId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const tId = typeof link.target === 'object' ? (link.target as any).id : link.target
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
    data.links.forEach(link => {
      const sId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const tId = typeof link.target === 'object' ? (link.target as any).id : link.target
      if (sId === selectedNode.id || tId === selectedNode.id) {
        set.add(link)
      }
    })
    return set
  }, [selectedNode, data])

  // 计算选中节点的详细三元组关系列表
  const nodeRelations = React.useMemo(() => {
    if (!selectedNode || !data) return []
    return data.links.filter(link => {
      const sId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const tId = typeof link.target === 'object' ? (link.target as any).id : link.target
      return sId === selectedNode.id || tId === selectedNode.id
    }).map(link => {
      const sId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const tId = typeof link.target === 'object' ? (link.target as any).id : link.target
      const sourceNode = data.nodes.find(n => n.id === sId)
      const targetNode = data.nodes.find(n => n.id === tId)
      return {
        source: sId,
        sourceGroup: sourceNode?.group || "other",
        target: tId,
        targetGroup: targetNode?.group || "other",
        label: link.label
      }
    })
  }, [selectedNode, data])

  // 平滑聚焦节点
  const focusOnNode = useCallback((nodeId: string) => {
    if (!data || !graphRef.current) return
    const node = data.nodes.find(n => n.id === nodeId)
    if (node) {
      const n = node as any
      // 允许力导向图加载后再定位
      setTimeout(() => {
        if (typeof n.x === 'number' && typeof n.y === 'number') {
          graphRef.current.centerAt(n.x, n.y, 800)
          graphRef.current.zoom(2.2, 800)
        }
      }, 50)
    }
  }, [data])

  const selectAndFocusNode = useCallback((nodeId: string, group: string) => {
    setSelectedNode({ id: nodeId, group })
    focusOnNode(nodeId)
  }, [focusOnNode])

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        })
      }
    }
    updateDimensions()
    window.addEventListener("resize", updateDimensions)
    return () => window.removeEventListener("resize", updateDimensions)
  }, [])

  const getNodeColor = (group: string) => {
    switch (group) {
      case "character": return isDark ? "#34d399" : "#059669" // emerald
      case "item": return isDark ? "#facc15" : "#ca8a04"      // yellow
      case "location": return isDark ? "#60a5fa" : "#2563eb"  // blue
      case "faction": return isDark ? "#f472b6" : "#db2777"   // pink
      default: return isDark ? "#9ca3af" : "#4b5563"          // gray
    }
  }

  const getGroupNameZh = (group: string) => {
    switch (group) {
      case "character": return "角色"
      case "item": return "物品"
      case "location": return "地点"
      case "faction": return "势力"
      default: return "未知"
    }
  }

  if (loading) {
    return (
      <div className="flex h-full min-h-[400px] w-full items-center justify-center bg-background/50 rounded-lg border border-border">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">正在加载图谱记忆...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full min-h-[400px] w-full flex-col items-center justify-center gap-4 bg-background/50 rounded-lg border border-border">
        <p className="text-sm text-destructive">{error}</p>
        <button onClick={fetchGraph} className="flex items-center gap-2 text-sm hover:text-primary transition-colors">
          <RefreshCcw className="h-4 w-4" /> 重试
        </button>
      </div>
    )
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex h-full min-h-[400px] w-full items-center justify-center bg-background/50 rounded-lg border border-border text-sm text-muted-foreground">
        暂无图谱数据。系统将在每次写完新章节后自动抽取关系。
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative h-full min-h-[500px] w-full rounded-lg overflow-hidden border border-border bg-background shadow-inner flex flex-row">
      
      {/* 左侧图谱视图区 */}
      <div className="flex-1 h-full relative min-w-0">
        
        {/* 控制浮层：搜索与图例 */}
        <div className="absolute top-4 left-4 z-10 flex flex-col gap-3 w-64 max-w-full">
          {/* 实体搜索 */}
          <div className="bg-background/95 backdrop-blur-md border border-border p-2.5 rounded-xl shadow-xl flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="快速搜索实体..."
              className="w-full text-xs bg-transparent border-0 focus-visible:outline-none focus-visible:ring-0 text-foreground placeholder:text-muted-foreground/60"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="text-muted-foreground hover:text-foreground shrink-0">
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
          
          {/* 实体图例 */}
          <div className="bg-background/95 backdrop-blur-md border border-border p-3.5 rounded-xl shadow-xl text-[11px] font-medium text-muted-foreground">
            <div className="font-bold mb-2 text-foreground text-xs">图谱节点图例</div>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>角色</div>
              <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-yellow-500"></div>物品</div>
              <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-blue-500"></div>地点</div>
              <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-pink-500"></div>势力</div>
            </div>
          </div>
        </div>
        
        <button 
          onClick={fetchGraph} 
          className="absolute top-4 right-4 z-10 p-2.5 bg-background/80 backdrop-blur border border-border rounded-xl shadow-xl hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          title="刷新图谱"
        >
          <RefreshCcw className="h-4.5 w-4.5" />
        </button>

        <ForceGraph2D
          ref={graphRef}
          width={selectedNode ? dimensions.width - 320 : dimensions.width}
          height={dimensions.height}
          graphData={data}
          nodeColor={(node: any) => getNodeColor(node.group)}
          nodeLabel="id"
          nodeRelSize={6}
          linkColor={() => isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.15)"}
          linkWidth={(link: any) => {
            if (selectedNode && highlightLinks.has(link)) {
              return 3.5
            }
            return 1.5
          }}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.2}
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
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            const label = node.id
            const fontSize = 12 / globalScale
            ctx.font = `${fontSize}px Sans-Serif`
            const textWidth = ctx.measureText(label).width
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.25)
            
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

            // 如果是被选中的节点，绘制外层亮圈
            if (selectedNode && selectedNode.id === node.id) {
              ctx.shadowBlur = 15
              ctx.shadowColor = getNodeColor(node.group)
              ctx.strokeStyle = getNodeColor(node.group)
              ctx.lineWidth = 2.5 / globalScale
              ctx.strokeRect(node.x - bckgDimensions[0] / 2 - 2, node.y - bckgDimensions[1] / 2 - 2, bckgDimensions[0] + 4, bckgDimensions[1] + 4)
            }

            // 绘制半透明底色矩形
            ctx.fillStyle = isDark ? "rgba(10, 10, 10, 0.85)" : "rgba(255, 255, 255, 0.85)"
            ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1])

            // 绘制文字
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillStyle = getNodeColor(node.group)
            ctx.fillText(label, node.x, node.y)
            ctx.restore()

            node.__bckgDimensions = bckgDimensions
          }}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            ctx.fillStyle = color
            const bckgDimensions = node.__bckgDimensions
            if (bckgDimensions) {
              ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1])
            }
          }}
        />
      </div>

      {/* 右侧节点详情面板 */}
      {selectedNode && (
        <div className="w-[320px] shrink-0 border-l border-border bg-card/60 backdrop-blur-xl p-5 flex flex-col gap-4 animate-in slide-in-from-right duration-200 overflow-y-auto z-20">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <h3 className="font-extrabold text-base tracking-tight truncate flex-1 text-foreground">
              {selectedNode.id}
            </h3>
            <button 
              onClick={() => setSelectedNode(null)} 
              className="text-muted-foreground hover:text-foreground rounded-lg p-1.5 hover:bg-muted"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-4">
            {/* 实体类别 */}
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-muted-foreground/80 tracking-wider">实体类型</span>
              <div>
                <Badge 
                  variant="outline" 
                  className="px-2.5 py-1 border-primary/20 text-xs font-semibold"
                  style={{
                    color: getNodeColor(selectedNode.group),
                    borderColor: `${getNodeColor(selectedNode.group)}30`,
                    backgroundColor: `${getNodeColor(selectedNode.group)}10`
                  }}
                >
                  {getGroupNameZh(selectedNode.group)} ({selectedNode.group})
                </Badge>
              </div>
            </div>

            {/* 关联关系 */}
            <div className="space-y-2 flex-1 flex flex-col min-h-0">
              <span className="text-[10px] uppercase font-bold text-muted-foreground/80 tracking-wider flex items-center gap-1">
                <LinkIcon className="h-3 w-3" />
                关联三元组关系 ({nodeRelations.length})
              </span>
              
              {nodeRelations.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">暂无直接关联的其他节点。</p>
              ) : (
                <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
                  {nodeRelations.map((rel, idx) => {
                    const isSourceSelf = rel.source === selectedNode.id
                    const neighborId = isSourceSelf ? rel.target : rel.source
                    const neighborGroup = isSourceSelf ? rel.targetGroup : rel.sourceGroup
                    
                    return (
                      <div key={idx} className="p-2.5 rounded-xl border border-border/40 bg-muted/10 hover:bg-muted/20 transition-all text-xs">
                        <div className="flex flex-wrap items-center gap-1 leading-relaxed">
                          <span 
                            onClick={() => !isSourceSelf && selectAndFocusNode(rel.source, rel.sourceGroup)}
                            className={`font-semibold cursor-pointer ${isSourceSelf ? "text-foreground" : "hover:text-primary hover:underline"}`}
                            style={!isSourceSelf ? { color: getNodeColor(rel.sourceGroup) } : {}}
                          >
                            {rel.source}
                          </span>
                          <span className="text-muted-foreground font-mono text-[10px] px-1 bg-muted rounded border border-border/20">
                            {rel.label}
                          </span>
                          <span 
                            onClick={() => isSourceSelf && selectAndFocusNode(rel.target, rel.targetGroup)}
                            className={`font-semibold cursor-pointer ${!isSourceSelf ? "text-foreground" : "hover:text-primary hover:underline"}`}
                            style={isSourceSelf ? { color: getNodeColor(rel.targetGroup) } : {}}
                          >
                            {rel.target}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
