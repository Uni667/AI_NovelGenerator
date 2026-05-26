"use client"

import { useState, useEffect, useCallback } from "react"
import { useProjectContext } from "./ProjectContext"
import { api } from "@/lib/api-client"
import type { ProjectAnalytics, DailyTrendAnalytics } from "@/lib/types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  BarChart3, 
  Activity, 
  DollarSign, 
  Zap, 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle2, 
  Database,
  Clock,
  Layers
} from "lucide-react"
import { toast } from "sonner"

export function AnalyticsTab() {
  const { projectId } = useProjectContext()
  const [data, setData] = useState<ProjectAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [hoveredDay, setHoveredDay] = useState<DailyTrendAnalytics | null>(null)

  const fetchAnalytics = useCallback(async (isRefresh = false) => {
    if (!projectId) return
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    try {
      const res = await api.analytics.get(projectId)
      setData(res)
      if (res.daily_trend && res.daily_trend.length > 0) {
        setHoveredDay(res.daily_trend[res.daily_trend.length - 1])
      }
    } catch (e) {
      console.error(e)
      toast.error("获取统计日志失败：" + (e as Error).message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div className="space-y-1">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton className="h-10 w-24" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-[350px] lg:col-span-2 rounded-xl" />
          <Skeleton className="h-[350px] rounded-xl" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-[300px] rounded-xl" />
          <Skeleton className="h-[300px] rounded-xl" />
        </div>
      </div>
    )
  }

  const summary = data?.summary || {
    total_calls: 0,
    success_rate: 0,
    avg_latency_ms: 0,
    total_input_chars: 0,
    total_output_chars: 0,
    estimated_cost_cny: 0
  }

  // 辅助渲染 SVG Sparkline / 折线图
  const renderTrendChart = () => {
    const trend = data?.daily_trend || []
    if (trend.length === 0) {
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
          暂无历史趋势数据
        </div>
      )
    }

    const width = 600
    const height = 220
    const padding = 40
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2

    // 计算最大最小值以做缩放
    const maxCalls = Math.max(...trend.map(d => d.count), 5)
    const maxCost = Math.max(...trend.map(d => d.estimated_cost_cny), 0.1)

    const stepX = trend.length > 1 ? chartWidth / (trend.length - 1) : chartWidth

    // 生成 Calls 折线点
    const callPoints = trend.map((d, i) => {
      const x = padding + i * stepX
      const y = height - padding - (d.count / maxCalls) * chartHeight
      return { x, y, data: d }
    })

    // 生成 Cost 折线点
    const costPoints = trend.map((d, i) => {
      const x = padding + i * stepX
      const y = height - padding - (d.estimated_cost_cny / maxCost) * chartHeight
      return { x, y, data: d }
    })

    const callPath = callPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
    const costPath = costPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')

    // 面积区域
    const callAreaPath = callPoints.length > 0 
      ? `${callPath} L ${callPoints[callPoints.length - 1].x} ${height - padding} L ${callPoints[0].x} ${height - padding} Z`
      : ''

    const costAreaPath = costPoints.length > 0 
      ? `${costPath} L ${costPoints[costPoints.length - 1].x} ${height - padding} L ${costPoints[0].x} ${height - padding} Z`
      : ''

    return (
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
          <defs>
            <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ec4899" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#ec4899" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* 网格背景线 */}
          {Array.from({ length: 5 }).map((_, i) => {
            const y = padding + (chartHeight / 4) * i
            return (
              <line 
                key={i} 
                x1={padding} 
                y1={y} 
                x2={width - padding} 
                y2={y} 
                stroke="currentColor" 
                className="text-border/30" 
                strokeDasharray="4 4" 
              />
            )
          })}

          {/* 填充面积 */}
          {callPoints.length > 0 && (
            <path d={callAreaPath} fill="url(#callsGrad)" className="transition-all duration-300" />
          )}
          {costPoints.length > 0 && (
            <path d={costAreaPath} fill="url(#costGrad)" className="transition-all duration-300" />
          )}

          {/* 绘制折线 */}
          <path d={callPath} fill="none" stroke="hsl(var(--primary))" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-all duration-300" />
          <path d={costPath} fill="none" stroke="#ec4899" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="3 1" className="transition-all duration-300" />

          {/* 数据点交互圈 */}
          {callPoints.map((p, i) => (
            <g key={i} className="cursor-pointer group/dot" onMouseEnter={() => setHoveredDay(p.data)}>
              {/* 外圈高亮 */}
              <circle 
                cx={p.x} 
                cy={p.y} 
                r="7" 
                fill="hsl(var(--primary))" 
                className="opacity-0 group-hover/dot:opacity-30 transition-opacity duration-200" 
              />
              {/* 实心小圆 */}
              <circle 
                cx={p.x} 
                cy={p.y} 
                r="3.5" 
                fill="hsl(var(--background))" 
                stroke="hsl(var(--primary))" 
                strokeWidth="2" 
                className="transition-all duration-200 group-hover/dot:scale-125"
              />
            </g>
          ))}

          {/* X 轴标签 */}
          {trend.length > 0 && (
            <>
              {/* 第一个 */}
              <text x={padding} y={height - padding + 18} textAnchor="start" className="fill-muted-foreground text-[10px] font-mono">
                {trend[0].date.slice(5)}
              </text>
              {/* 中间 */}
              {trend.length > 2 && (
                <text x={width / 2} y={height - padding + 18} textAnchor="middle" className="fill-muted-foreground text-[10px] font-mono">
                  {trend[Math.floor(trend.length / 2)].date.slice(5)}
                </text>
              )}
              {/* 最后一个 */}
              <text x={width - padding} y={height - padding + 18} textAnchor="end" className="fill-muted-foreground text-[10px] font-mono">
                {trend[trend.length - 1].date.slice(5)}
              </text>
            </>
          )}

          {/* 左右 Y 轴最大值指示 */}
          <text x={padding - 6} y={padding + 4} textAnchor="end" className="fill-primary text-[9px] font-bold font-mono">
            {maxCalls}次
          </text>
          <text x={width - padding + 6} y={padding + 4} textAnchor="start" className="fill-pink-500 text-[9px] font-bold font-mono">
            ￥{maxCost.toFixed(2)}
          </text>
        </svg>

        {/* 悬浮信息提示板 */}
        {hoveredDay && (
          <div className="absolute top-2 left-10 right-10 bg-background/80 backdrop-blur-md border border-border/60 rounded-lg p-2.5 flex items-center justify-between shadow-md text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-foreground">{hoveredDay.date}</span>
              <Badge variant="outline" className="text-[10px] font-mono px-1 py-0 h-4 bg-muted text-muted-foreground">
                统计数据
              </Badge>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-primary" />
                <span className="text-muted-foreground">调用:</span>
                <span className="font-bold font-mono text-foreground">{hoveredDay.count}次</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-pink-500" />
                <span className="text-muted-foreground">估算:</span>
                <span className="font-bold font-mono text-pink-500">￥{hoveredDay.estimated_cost_cny.toFixed(4)}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">成功率:</span>
                <span className={`font-mono font-bold ${hoveredDay.success_rate >= 0.9 ? 'text-green-400' : hoveredDay.success_rate >= 0.7 ? 'text-amber-400' : 'text-red-400'}`}>
                  {(hoveredDay.success_rate * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // 格式化时长
  const formatDuration = (ms: number) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`
    }
    return `${ms.toFixed(0)}ms`
  }

  // 根据延时评估性能评级
  const getLatencyGrade = (ms: number) => {
    if (ms === 0) return { label: "暂无数据", color: "bg-muted text-muted-foreground" }
    if (ms < 2000) return { label: "极速", color: "bg-green-500/10 text-green-400 border-green-500/20" }
    if (ms < 5000) return { label: "正常", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" }
    if (ms < 10000) return { label: "较慢", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" }
    return { label: "超时预警", color: "bg-red-500/10 text-red-400 border-red-500/20 animate-pulse" }
  }

  // 用途中文转换
  const translatePurpose = (p: string) => {
    const maps: Record<string, string> = {
      "general": "通用对话",
      "draft": "小说起草",
      "outline": "大纲规划",
      "brainstorm": "多角色脑暴",
      "qa": "内容质检",
      "summary": "章节压缩",
      "architect": "雪花架构"
    }
    return maps[p.toLowerCase()] || p
  }

  return (
    <div className="space-y-6">
      {/* 顶部控制栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-purple-400" />
            API 开销与响应日志监控
          </h2>
          <p className="text-sm text-muted-foreground">
            实时查看大模型调用次数、耗时效率、字数负载与估算推理资费。
          </p>
        </div>
        
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => fetchAnalytics(true)}
          disabled={refreshing}
          className="border-primary/20 bg-primary/5 hover:bg-primary/10 transition-colors w-full sm:w-auto"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新日志统计
        </Button>
      </div>

      {/* 4个核心指标卡片 Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 卡片 1: 推理资费 */}
        <Card className="relative overflow-hidden bg-background/40 backdrop-blur-md border-border/40 hover:scale-[1.01] hover:border-primary/30 transition-all duration-300 shadow-md">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-full blur-2xl" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5 text-purple-400" />
              估算资费 (CNY)
            </CardTitle>
            <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/20 text-[10px]">累计消耗</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground">
              ￥{summary.estimated_cost_cny.toFixed(4)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1 flex items-center justify-between">
              <span>单次均价: ￥{summary.total_calls > 0 ? (summary.estimated_cost_cny / summary.total_calls).toFixed(5) : "0.00000"}</span>
            </div>
          </CardContent>
        </Card>

        {/* 卡片 2: 调用成功率 */}
        <Card className="relative overflow-hidden bg-background/40 backdrop-blur-md border-border/40 hover:scale-[1.01] hover:border-primary/30 transition-all duration-300 shadow-md">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-emerald-500/10 to-green-500/10 rounded-full blur-2xl" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-emerald-400" />
              服务成功率
            </CardTitle>
            <Badge 
              variant="outline" 
              className={`text-[10px] ${summary.success_rate >= 0.9 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : summary.success_rate >= 0.7 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse'}`}
            >
              {summary.success_rate >= 0.95 ? "极稳定" : summary.success_rate >= 0.8 ? "良好" : "故障频发"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground flex items-baseline gap-1">
              {(summary.success_rate * 100).toFixed(1)}
              <span className="text-xs font-normal text-muted-foreground">%</span>
            </div>
            <div className="text-[10px] text-muted-foreground mt-1 flex items-center justify-between">
              <span>总调用: {summary.total_calls}次</span>
              <span className="text-red-400">失败: {summary.total_calls - Math.round(summary.total_calls * summary.success_rate)}次</span>
            </div>
          </CardContent>
        </Card>

        {/* 卡片 3: 响应平均延时 */}
        <Card className="relative overflow-hidden bg-background/40 backdrop-blur-md border-border/40 hover:scale-[1.01] hover:border-primary/30 transition-all duration-300 shadow-md">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-blue-500/10 to-teal-500/10 rounded-full blur-2xl" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-blue-400" />
              响应平均延时
            </CardTitle>
            <Badge variant="outline" className={`${getLatencyGrade(summary.avg_latency_ms).color} text-[10px]`}>
              {getLatencyGrade(summary.avg_latency_ms).label}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground">
              {formatDuration(summary.avg_latency_ms)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              基于有效调用时间做加权计算
            </div>
          </CardContent>
        </Card>

        {/* 卡片 4: 吞吐字符数 */}
        <Card className="relative overflow-hidden bg-background/40 backdrop-blur-md border-border/40 hover:scale-[1.01] hover:border-primary/30 transition-all duration-300 shadow-md">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-amber-500/10 to-yellow-500/10 rounded-full blur-2xl" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-amber-400" />
              上下文吞吐量
            </CardTitle>
            <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]">字符统计</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground flex items-baseline gap-1">
              {((summary.total_input_chars + summary.total_output_chars) / 1000).toFixed(1)}
              <span className="text-xs font-normal text-muted-foreground">K字</span>
            </div>
            <div className="text-[10px] text-muted-foreground mt-1 flex items-center justify-between">
              <span>输入: {(summary.total_input_chars / 1000).toFixed(1)}k</span>
              <span>输出: {(summary.total_output_chars / 1000).toFixed(1)}k</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 趋势折线图 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  30天模型调用与资费趋势
                </CardTitle>
                <CardDescription className="text-xs">
                  实线代表每日调用频次，虚线表示每日估算推理资费。
                </CardDescription>
              </div>
              <div className="flex gap-3 text-[10px] font-mono">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-primary inline-block" />
                  调用次数 (左轴)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 border-t border-pink-500 border-dashed inline-block" />
                  资费 CNY (右轴)
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            {renderTrendChart()}
          </CardContent>
        </Card>

        {/* 模型分类开销统计 */}
        <Card className="bg-background/40 backdrop-blur-md border-border/40 shadow-lg flex flex-col">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="h-4 w-4 text-purple-400" />
              模型开销占比排行
            </CardTitle>
            <CardDescription className="text-xs">
              按计费模型聚合。优先优化占比高的模型。
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col justify-between pt-3">
            <div className="space-y-4 max-h-[220px] overflow-y-auto pr-1">
              {data?.by_model && data.by_model.length > 0 ? (
                data.by_model.map((m, index) => {
                  const maxCost = data.by_model[0]?.estimated_cost_cny || 1
                  const percentage = (m.estimated_cost_cny / maxCost) * 100
                  return (
                    <div key={index} className="space-y-1">
                      <div className="flex justify-between text-xs items-center">
                        <div className="font-medium truncate max-w-[150px] text-foreground" title={m.model}>
                          {m.model}
                        </div>
                        <div className="font-mono text-muted-foreground flex gap-2">
                          <span>{m.count}次</span>
                          <span className="text-pink-500 font-bold">￥{m.estimated_cost_cny.toFixed(3)}</span>
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500" 
                          style={{ width: `${Math.max(percentage, 2)}%` }} 
                        />
                      </div>
                    </div>
                  )
                })
              ) : (
                <div className="text-center text-muted-foreground py-10 text-xs">
                  暂无模型调用数据
                </div>
              )}
            </div>
            
            {data?.by_model && data.by_model.length > 0 && (
              <div className="border-t border-border/40 pt-2.5 mt-2.5 text-[10px] text-muted-foreground flex justify-between">
                <span>最高开销: {data.by_model[0]?.model.slice(0, 15)}...</span>
                <span>共有 {data.by_model.length} 种模型</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 模型用途统计 与 报错统计 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 用途统计 */}
        <Card className="bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-400" />
              小说创作阶段频次占比
            </CardTitle>
            <CardDescription className="text-xs">
              统计大模型在不同业务节点（起草、脑暴、质检等）的调用频次。
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <ScrollArea className="h-[200px] pr-3">
              <div className="space-y-4">
                {data?.by_purpose && data.by_purpose.length > 0 ? (
                  data.by_purpose.map((p, index) => {
                    const total = summary.total_calls || 1
                    const percentage = (p.count / total) * 100
                    return (
                      <div key={index} className="space-y-1.5">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-medium text-foreground">{translatePurpose(p.purpose)}</span>
                          <span className="font-mono text-muted-foreground">
                            {p.count}次 ({(p.success_rate * 100).toFixed(0)}%成功率)
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full" 
                              style={{ width: `${percentage}%` }} 
                            />
                          </div>
                          <span className="text-[10px] font-mono font-bold text-muted-foreground min-w-[30px] text-right">
                            {percentage.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    )
                  })
                ) : (
                  <div className="text-center text-muted-foreground py-10 text-xs">
                    暂无业务维度统计数据
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* 异常与报错率分析 */}
        <Card className="bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              API 异常与报错分析
            </CardTitle>
            <CardDescription className="text-xs">
              汇总调用失败的原因与错误代码，帮助定位模型连通性与服务商额度问题。
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <ScrollArea className="h-[200px] pr-3">
              <div className="space-y-4">
                {data?.errors && data.errors.length > 0 ? (
                  data.errors.map((e, index) => {
                    const maxError = Math.max(...data.errors.map(x => x.count), 1)
                    const percentage = (e.count / maxError) * 100
                    return (
                      <div key={index} className="border border-border/50 bg-muted/20 rounded-lg p-2.5 space-y-1.5 transition-all hover:bg-muted/40">
                        <div className="flex justify-between items-center text-xs">
                          <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20 font-mono text-[10px]">
                            {e.error_code}
                          </Badge>
                          <span className="font-mono text-muted-foreground font-bold">{e.count}次发生</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono leading-relaxed line-clamp-2" title={e.last_message}>
                          最新描述: {e.last_message || "无详细错误信息描述"}
                        </div>
                        <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-red-400 rounded-full" 
                            style={{ width: `${percentage}%` }} 
                          />
                        </div>
                      </div>
                    )
                  })
                ) : (
                  <div className="h-[160px] flex flex-col items-center justify-center text-center">
                    <CheckCircle2 className="h-8 w-8 text-green-400 mb-2" />
                    <p className="text-xs font-bold text-foreground">未检测到任何调用错误</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">小说创作流水线当前运行非常平稳。</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* 服务商维度对比统计 */}
      <Card className="bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Database className="h-4 w-4 text-emerald-400" />
            服务商可用性与性能横向对比
          </CardTitle>
          <CardDescription className="text-xs">
            横向对比各大接口渠道（硅基流动、DeepSeek 原生、OpenAI 等）的吞吐表现。
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-2">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border/60 text-muted-foreground font-semibold">
                  <th className="pb-3 pt-1">服务商 Channel</th>
                  <th className="pb-3 pt-1">调用频次</th>
                  <th className="pb-3 pt-1">平均响应时长</th>
                  <th className="pb-3 pt-1">可用成功率</th>
                  <th className="pb-3 pt-1 text-right">消耗推理资费</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 font-medium">
                {data?.by_provider && data.by_provider.length > 0 ? (
                  data.by_provider.map((p, index) => (
                    <tr key={index} className="hover:bg-muted/10 transition-colors">
                      <td className="py-3 font-semibold text-foreground capitalize flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {p.provider}
                      </td>
                      <td className="py-3 font-mono">{p.count} 次</td>
                      <td className="py-3 font-mono">{formatDuration(p.avg_latency_ms)}</td>
                      <td className="py-3">
                        <Badge 
                          variant="outline" 
                          className={`font-mono text-[10px] ${p.success_rate >= 0.9 ? 'bg-green-500/10 text-green-400 border-green-500/20' : p.success_rate >= 0.7 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}
                        >
                          {(p.success_rate * 100).toFixed(0)}%
                        </Badge>
                      </td>
                      <td className="py-3 text-right font-mono font-bold text-pink-500">￥{p.estimated_cost_cny.toFixed(4)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="text-center py-10 text-muted-foreground text-xs">
                      暂无可用服务商数据进行比对
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
