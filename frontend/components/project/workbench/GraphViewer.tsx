"use client"

import React, { useEffect, useRef, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { useProjectContext } from "../ProjectContext"
import { Loader2, RefreshCcw } from "lucide-react"
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d"
import { useTheme } from "next-themes"

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
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined)

  const isDark = resolvedTheme === "dark" || theme === "dark"

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
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
    <div ref={containerRef} className="relative h-full min-h-[500px] w-full rounded-lg overflow-hidden border border-border bg-background shadow-inner">
      <div className="absolute top-4 left-4 z-10 bg-background/80 backdrop-blur border border-border p-3 rounded-lg shadow-sm text-xs">
        <div className="font-semibold mb-2 text-foreground">实体图例</div>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500"></div>角色 (Character)</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-yellow-500"></div>物品 (Item)</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-blue-500"></div>地点 (Location)</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-pink-500"></div>势力 (Faction)</div>
        </div>
      </div>
      
      <button 
        onClick={fetchGraph} 
        className="absolute top-4 right-4 z-10 p-2 bg-background/80 backdrop-blur border border-border rounded-lg shadow-sm hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
        title="刷新图谱"
      >
        <RefreshCcw className="h-4 w-4" />
      </button>

      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={data}
        nodeColor={(node: any) => getNodeColor(node.group)}
        nodeLabel="id"
        nodeRelSize={6}
        linkColor={() => isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.15)"}
        linkWidth={1.5}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.2}
        linkLabel="label"
        backgroundColor={isDark ? "transparent" : "#f8fafc"}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.id
          const fontSize = 12 / globalScale
          ctx.font = `${fontSize}px Sans-Serif`
          const textWidth = ctx.measureText(label).width
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2)

          ctx.fillStyle = isDark ? "rgba(0, 0, 0, 0.8)" : "rgba(255, 255, 255, 0.8)"
          ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1])

          ctx.textAlign = "center"
          ctx.textBaseline = "middle"
          ctx.fillStyle = getNodeColor(node.group)
          ctx.fillText(label, node.x, node.y)

          node.__bckgDimensions = bckgDimensions // to re-use in nodePointerAreaPaint
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
  )
}
