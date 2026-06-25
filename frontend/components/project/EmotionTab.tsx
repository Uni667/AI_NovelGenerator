"use client"

import { useState, useEffect, useCallback } from "react"
import { useProjectContext } from "./ProjectContext"
import { api } from "@/lib/api-client"
import type { EmotionArcPoint, EmotionAnalysis } from "@/lib/types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import {
  TrendingUp,
  BarChart3,
  Activity,
  Smile,
  Frown,
  Meh,
  AlertCircle,
  RefreshCw,
  Play,
  CheckCircle2,
  HelpCircle,
  Send,
  Eye,
  Info,
  Sparkles
} from "lucide-react"
import { toast } from "sonner"

export function EmotionTab() {
  const { projectId } = useProjectContext()
  const [method, setMethod] = useState<string>("snownlp")
  const [arcData, setArcData] = useState<EmotionArcPoint[]>([])
  const [summary, setSummary] = useState<{
    avg_score: number
    max_score_chapter: number
    min_score_chapter: number
    chapter_count: number
  } | null>(null)
  
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [hoveredPoint, setHoveredPoint] = useState<EmotionArcPoint | null>(null)
  const [selectedPoint, setSelectedPoint] = useState<EmotionArcPoint | null>(null)

  // 单章分析状态
  const [selectedChapterNum, setSelectedChapterNum] = useState<string>("")
  const [singleAnalyzing, setSingleAnalyzing] = useState(false)

  // 快速测试状态
  const [quickText, setQuickText] = useState("")
  const [quickMethod, setQuickMethod] = useState("snownlp")
  const [quickResult, setQuickResult] = useState<EmotionAnalysis | null>(null)
  const [quickLoading, setQuickLoading] = useState(false)

  const fetchArcData = useCallback(async (showToast = false) => {
    if (!projectId) return
    setLoading(true)
    try {
      const res = await api.emotion.getArc(projectId, method)
      setArcData(res.arc || [])
      setSummary(res.summary as any || null)
      if (res.arc && res.arc.length > 0) {
        // 默认选中最后一章
        setSelectedPoint(res.arc[res.arc.length - 1])
        if (selectedChapterNum === "") {
          setSelectedChapterNum(String(res.arc[res.arc.length - 1].chapter_number))
        }
      }
      if (showToast) {
        toast.success("情感弧线加载成功")
      }
    } catch (e: any) {
      console.error(e)
      toast.error("加载情感数据失败: " + e.message)
    } finally {
      setLoading(false)
    }
  }, [projectId, method])

  useEffect(() => {
    fetchArcData()
  }, [fetchArcData])

  // 执行全书分析
  const handleAnalyzeAll = async () => {
    if (!projectId) return
    setAnalyzing(true)
    toast.info("正在对整本小说章节进行情感分析，这可能需要一些时间...")
    try {
      // 通过 getArc API 触发后台分析
      const res = await api.emotion.getArc(projectId, method)
      setArcData(res.arc || [])
      setSummary(res.summary as any || null)
      if (res.arc && res.arc.length > 0) {
        setSelectedPoint(res.arc[res.arc.length - 1])
      }
      toast.success("全书章节情感分析完成")
    } catch (e: any) {
      console.error(e)
      toast.error("情感分析失败: " + e.message)
    } finally {
      setAnalyzing(false)
    }
  }

  // 分析单章
  const handleAnalyzeSingle = async () => {
    if (!projectId || !selectedChapterNum) return
    const chNum = parseInt(selectedChapterNum)
    if (isNaN(chNum)) return

    setSingleAnalyzing(true)
    toast.info(`正在分析第 ${chNum} 章情感...`)
    try {
      const res = await api.emotion.analyzeChapter(projectId, chNum, method)
      toast.success(`第 ${chNum} 章情感分析完成`)
      // 重新加载图表以更新对应章节
      await fetchArcData()
      // 更新当前选中的点
      if (res.analysis) {
        const updatedPoint: EmotionArcPoint = {
          chapter_number: chNum,
          title: `第${chNum}章`,
          score: res.analysis.score,
          label: res.analysis.label,
          detail: res.analysis
        }
        setSelectedPoint(updatedPoint)
      }
    } catch (e: any) {
      console.error(e)
      toast.error(`分析第 ${chNum} 章失败: ` + e.message)
    } finally {
      setSingleAnalyzing(false)
    }
  }

  // 运行快速测试
  const handleQuickTest = async () => {
    if (!quickText.trim()) {
      toast.warning("请输入测试文本")
      return
    }
    setQuickLoading(true)
    try {
      const res = await api.emotion.quickAnalyze(quickText, quickMethod)
      setQuickResult(res.analysis)
      toast.success("快速分析完成")
    } catch (e: any) {
      console.error(e)
      toast.error("测试分析失败: " + e.message)
    } finally {
      setQuickLoading(false)
    }
  }

  // 格式化标签与颜色
  const getEmotionColor = (label: string) => {
    switch (label) {
      case "积极":
      case "喜悦":
        return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
      case "消极":
      case "悲伤":
      case "愤怒":
        return "text-red-400 border-red-500/30 bg-red-500/10"
      case "紧张":
        return "text-amber-400 border-amber-500/30 bg-amber-500/10"
      default:
        return "text-slate-400 border-slate-500/30 bg-slate-500/10"
    }
  }

  const getScoreEmoji = (score: number) => {
    if (score >= 0.7) return <Smile className="h-4 w-4 text-emerald-400" />
    if (score <= 0.35) return <Frown className="h-4 w-4 text-red-400" />
    return <Meh className="h-4 w-4 text-slate-400" />
  }

  // 绘制 SVG 折线图
  const renderSvgChart = () => {
    if (arcData.length === 0) {
      return (
        <div className="h-[250px] flex flex-col items-center justify-center text-muted-foreground bg-background/20 rounded-xl border border-dashed border-border/40 p-6">
          <Activity className="h-8 w-8 text-muted-foreground/40 mb-2 animate-pulse" />
          <p className="text-sm">暂无本小说章节的情感分析数据</p>
          <Button onClick={handleAnalyzeAll} disabled={analyzing} className="mt-4 shadow-md bg-primary hover:bg-primary/90">
            {analyzing ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            开始分析全书章节
          </Button>
        </div>
      )
    }

    const width = 800
    const height = 260
    const paddingLeft = 50
    const paddingRight = 30
    const paddingTop = 30
    const paddingBottom = 40
    const chartWidth = width - paddingLeft - paddingRight
    const chartHeight = height - paddingTop - paddingBottom

    const stepX = arcData.length > 1 ? chartWidth / (arcData.length - 1) : chartWidth

    // 点转换逻辑
    const points = arcData.map((d, i) => {
      const x = paddingLeft + i * stepX
      // Y 轴反转：0.0 在底部，1.0 在顶部
      const y = height - paddingBottom - d.score * chartHeight
      return { x, y, data: d }
    })

    const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ")
    
    // 渐变面积路径（封闭到 Y = 0.5 或者是底部）
    const areaPath = points.length > 0
      ? `${linePath} L ${points[points.length - 1].x} ${height - paddingBottom} L ${points[0].x} ${height - paddingBottom} Z`
      : ""

    // 0.5 黄金中值分水岭
    const yBaseline = height - paddingBottom - 0.5 * chartHeight

    return (
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
          <defs>
            {/* 曲线渐变色 (积极->消极) */}
            <linearGradient id="emotionStrokeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" /> {/* 积极: 绿 */}
              <stop offset="50%" stopColor="#eab308" /> {/* 中性: 黄 */}
              <stop offset="100%" stopColor="#ef4444" /> {/* 消极: 红 */}
            </linearGradient>

            {/* 填充面积渐变色 */}
            <linearGradient id="emotionAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
              <stop offset="50%" stopColor="#eab308" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.03" />
            </linearGradient>
          </defs>

          {/* 网格水平参考线 */}
          {Array.from({ length: 5 }).map((_, i) => {
            const val = 0.25 * i
            const y = height - paddingBottom - val * chartHeight
            return (
              <g key={i}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={width - paddingRight}
                  y2={y}
                  stroke="currentColor"
                  className={val === 0.5 ? "text-primary/30" : "text-border/20"}
                  strokeWidth={val === 0.5 ? "1.5" : "1"}
                  strokeDasharray={val === 0.5 ? "" : "4 4"}
                />
                <text x={paddingLeft - 8} y={y + 3} textAnchor="end" className="fill-muted-foreground text-[10px] font-mono">
                  {val.toFixed(2)}
                </text>
              </g>
            )
          })}

          {/* X 轴线 */}
          <line
            x1={paddingLeft}
            y1={height - paddingBottom}
            x2={width - paddingRight}
            y2={height - paddingBottom}
            stroke="currentColor"
            className="text-border"
          />

          {/* 填充区域 */}
          {points.length > 0 && (
            <path d={areaPath} fill="url(#emotionAreaGrad)" className="transition-all duration-300" />
          )}

          {/* 绘制情感曲线 */}
          {points.length > 0 && (
            <path
              d={linePath}
              fill="none"
              stroke="url(#emotionStrokeGrad)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="transition-all duration-300"
            />
          )}

          {/* 黄金中值 baseline (0.5 中性) 提示 */}
          <line
            x1={paddingLeft}
            y1={yBaseline}
            x2={width - paddingRight}
            y2={yBaseline}
            stroke="currentColor"
            className="text-muted-foreground/30"
            strokeWidth="1"
            strokeDasharray="4 6"
          />
          <text x={width - paddingRight - 5} y={yBaseline - 5} textAnchor="end" className="fill-muted-foreground/60 text-[9px] font-mono">
            情感中基调 (0.50)
          </text>

          {/* 交互圆点 */}
          {points.map((p, i) => {
            const isHovered = hoveredPoint?.chapter_number === p.data.chapter_number
            const isSelected = selectedPoint?.chapter_number === p.data.chapter_number
            return (
              <g
                key={i}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredPoint(p.data)}
                onMouseLeave={() => setHoveredPoint(null)}
                onClick={() => setSelectedPoint(p.data)}
              >
                {/* 触发点击的隐形大圆 */}
                <circle cx={p.x} cy={p.y} r="12" fill="transparent" />

                {/* 交互高亮环 */}
                {(isHovered || isSelected) && (
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="8"
                    fill="currentColor"
                    className={`${isSelected ? "text-primary/20" : "text-primary/10"} animate-pulse`}
                  />
                )}

                {/* 实心数据点 */}
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isSelected ? "5" : "3.5"}
                  fill={isSelected ? "hsl(var(--primary))" : "hsl(var(--background))"}
                  stroke={isSelected ? "hsl(var(--background))" : "url(#emotionStrokeGrad)"}
                  strokeWidth="2.5"
                  className="transition-all duration-150"
                />
              </g>
            )
          })}

          {/* X 轴标签 (章节号) */}
          {arcData.length > 0 && (
            <>
              {/* 第一个章节 */}
              <text x={paddingLeft} y={height - paddingBottom + 16} textAnchor="middle" className="fill-muted-foreground text-[10px] font-mono">
                {arcData[0].title || `第${arcData[0].chapter_number}章`}
              </text>
              {/* 中间章节 */}
              {arcData.length > 2 && (
                <text x={width / 2} y={height - paddingBottom + 16} textAnchor="middle" className="fill-muted-foreground text-[10px] font-mono">
                  {arcData[Math.floor(arcData.length / 2)].title || `第${arcData[Math.floor(arcData.length / 2)].chapter_number}章`}
                </text>
              )}
              {/* 最后一个章节 */}
              {arcData.length > 1 && (
                <text x={width - paddingRight} y={height - paddingBottom + 16} textAnchor="middle" className="fill-muted-foreground text-[10px] font-mono">
                  {arcData[arcData.length - 1].title || `第${arcData[arcData.length - 1].chapter_number}章`}
                </text>
              )}
            </>
          )}
        </svg>

        {/* 悬停 Tooltip */}
        {hoveredPoint && (
          <div
            className="absolute top-2 left-1/2 transform -translate-x-1/2 bg-background/95 backdrop-blur-md border border-border/80 rounded-xl p-2.5 flex items-center gap-4 shadow-xl text-xs z-10 transition-opacity"
            style={{ width: "fit-content" }}
          >
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-foreground">{hoveredPoint.title}</span>
              <Badge className={`text-[10px] font-mono px-1.5 py-0 h-4 ${getEmotionColor(hoveredPoint.label)}`}>
                {hoveredPoint.label}
              </Badge>
            </div>
            <div className="flex items-center gap-2 font-mono">
              <span className="text-muted-foreground">得分:</span>
              <span className="font-bold text-foreground">{hoveredPoint.score.toFixed(3)}</span>
              {getScoreEmoji(hoveredPoint.score)}
            </div>
          </div>
        )}
      </div>
    )
  }

  // 渲染选中章节的详细分析报告
  const renderDetailReport = () => {
    if (!selectedPoint) {
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground text-sm py-12">
          请在折线图上选择一个章节查看情感分析详情。
        </div>
      )
    }

    const detail: EmotionAnalysis | undefined = selectedPoint.detail
    const hasDetail = !!detail

    return (
      <Card className="glass-panel border-border/30 bg-background/20 backdrop-blur-sm overflow-hidden h-full flex flex-col shadow-lg">
        <CardHeader className="pb-3 border-b border-border/40 shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-bold flex items-center gap-2">
              <Eye className="h-4 w-4 text-primary" />
              {selectedPoint.title} 情感分析报告
            </CardTitle>
            <Badge className={`text-xs px-2 py-0.5 font-semibold ${getEmotionColor(selectedPoint.label)}`}>
              {selectedPoint.label} 基调
            </Badge>
          </div>
          <CardDescription className="text-xs">
            分析方法：{detail?.method || method} | 情感得分：<span className="font-mono font-bold text-foreground">{selectedPoint.score.toFixed(3)}</span>
          </CardDescription>
        </CardHeader>
        
        <CardContent className="flex-1 overflow-y-auto pt-4 space-y-4 pr-3">
          {/* 大模型分析报告特有字段 */}
          {hasDetail && detail.method === "llm" && (
            <>
              {detail.tension !== undefined && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs items-center">
                    <span className="text-muted-foreground flex items-center gap-1"><Info className="h-3 w-3" /> 剧本张力强度</span>
                    <span className="font-mono font-semibold">{(detail.tension * 100).toFixed(0)}%</span>
                  </div>
                  <Progress value={detail.tension * 100} className="h-1.5 bg-muted" />
                </div>
              )}

              {detail.reasoning && (
                <div className="rounded-lg bg-muted/40 p-3 border border-border/40 text-xs">
                  <span className="font-bold text-primary block mb-1">🧠 判定逻辑：</span>
                  <p className="text-muted-foreground leading-relaxed italic">&quot;{detail.reasoning}&quot;</p>
                </div>
              )}

              {detail.key_emotions && detail.key_emotions.length > 0 && (
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">核心情绪词</span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {detail.key_emotions.map((emo, idx) => (
                      <Badge key={idx} variant="outline" className="text-[10px] py-0 border-border/60 bg-background/60">
                        {emo}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* 词典匹配法特有字段 */}
          {hasDetail && detail.method === "keyword" && (
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="border border-border/40 rounded-lg p-2.5 bg-emerald-500/5 space-y-1.5">
                <span className="text-emerald-400 font-bold flex items-center gap-1"><Smile className="h-3 w-3" /> 积极词汇 ({detail.pos_count || 0})</span>
                <ScrollArea className="h-20">
                  <div className="flex flex-wrap gap-1">
                    {detail.matched_positive && detail.matched_positive.length > 0 ? (
                      detail.matched_positive.map((word, idx) => (
                        <Badge key={idx} variant="outline" className="text-[9px] py-0 border-emerald-500/20 text-emerald-300 bg-emerald-950/20">
                          {word}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-[10px] text-muted-foreground">未匹配到</span>
                    )}
                  </div>
                </ScrollArea>
              </div>

              <div className="border border-border/40 rounded-lg p-2.5 bg-red-500/5 space-y-1.5">
                <span className="text-red-400 font-bold flex items-center gap-1"><Frown className="h-3 w-3" /> 消极词汇 ({detail.neg_count || 0})</span>
                <ScrollArea className="h-20">
                  <div className="flex flex-wrap gap-1">
                    {detail.matched_negative && detail.matched_negative.length > 0 ? (
                      detail.matched_negative.map((word, idx) => (
                        <Badge key={idx} variant="outline" className="text-[9px] py-0 border-red-500/20 text-red-300 bg-red-950/20">
                          {word}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-[10px] text-muted-foreground">未匹配到</span>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}

          {/* 分句分数趋势 (SnowNLP) */}
          {hasDetail && detail.method === "snownlp" && detail.sentence_scores && detail.sentence_scores.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs text-muted-foreground flex items-center gap-1"><BarChart3 className="h-3.5 w-3.5" /> 句级情感波动趋势</span>
              <div className="h-14 flex items-end gap-1 border-b border-border/40 pb-1 pt-2">
                {detail.sentence_scores.map((score, idx) => (
                  <div
                    key={idx}
                    className="flex-1 rounded-t transition-all hover:opacity-80"
                    style={{
                      height: `${score * 100}%`,
                      backgroundColor: score >= 0.65 ? "#10b981" : score <= 0.35 ? "#ef4444" : "#eab308"
                    }}
                    title={`第 ${idx+1} 句得分: ${score.toFixed(2)}`}
                  />
                ))}
              </div>
              <span className="text-[10px] text-muted-foreground block text-right">前 {detail.sentence_scores.length} 句波动走势 (左起)</span>
            </div>
          )}

          {/* 综合/All 方法报告 */}
          {hasDetail && detail.method === "all" && (
            <div className="space-y-3.5">
              <div className="rounded-lg border border-border/40 p-2.5 space-y-2 text-xs">
                <div className="flex justify-between items-center text-[10px] text-muted-foreground">
                  <span>融合算法评分</span>
                  <span className="font-mono text-emerald-400 font-bold">{selectedPoint.score.toFixed(3)}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-[10px] text-center">
                  <div className="border border-border/40 rounded p-1">
                    <span className="text-muted-foreground block">SnowNLP</span>
                    <span className="font-bold text-foreground">{detail.snownlp?.score.toFixed(2) || "0.50"}</span>
                  </div>
                  <div className="border border-border/40 rounded p-1">
                    <span className="text-muted-foreground block">词典匹配</span>
                    <span className="font-bold text-foreground">{detail.keyword?.score.toFixed(2) || "0.50"}</span>
                  </div>
                  <div className="border border-border/40 rounded p-1">
                    <span className="text-muted-foreground block">LLM分析</span>
                    <span className="font-bold text-foreground">{detail.llm?.score.toFixed(2) || "0.50"}</span>
                  </div>
                </div>
              </div>
              {detail.llm?.reasoning && (
                <div className="rounded-lg bg-muted/40 p-2.5 text-[11px] text-muted-foreground italic border border-border/40">
                  <span className="font-bold text-primary block text-xs not-italic mb-0.5">🧠 LLM 判定原因:</span>
                  &quot;{detail.llm.reasoning}&quot;
                </div>
              )}
            </div>
          )}

          {!hasDetail && (
            <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground border border-dashed border-border/30 rounded-xl">
              <Info className="h-6 w-6 text-muted-foreground/30 mb-1" />
              <p className="text-xs">本章节为缓存基础分，缺少深层分解数据</p>
              <Button
                variant="link"
                size="sm"
                onClick={() => {
                  setSelectedChapterNum(String(selectedPoint.chapter_number))
                  handleAnalyzeSingle()
                }}
                className="text-primary hover:text-primary/80 text-xs mt-1"
              >
                立即发起深度 analysis
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* 顶部控制面板 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-indigo-400 bg-clip-text text-transparent flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
            小说情感弧线质量监控
          </h2>
          <p className="text-sm text-muted-foreground">
            利用自然语言处理(NLP)分析章节情感起伏，帮助创作者掌控剧情节奏，解决情感平淡与失真。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:self-end">
          {/* 分析方法下拉框 */}
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">分析算法：</span>
            <Select value={method} onValueChange={(val) => setMethod(val || "snownlp")}>
              <SelectTrigger className="w-[140px] h-9 border-border/60 bg-background/40 rounded-xl focus:ring-primary/40 text-xs">
                <SelectValue placeholder="算法方法" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="snownlp">词典法 (SnowNLP)</SelectItem>
                <SelectItem value="keyword">文学情感词典</SelectItem>
                <SelectItem value="llm">大模型零样本 (LLM)</SelectItem>
                <SelectItem value="all">混合算法 (All)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchArcData(true)}
            disabled={analyzing || loading}
            className="border-primary/20 bg-primary/5 hover:bg-primary/10 transition-colors h-9 text-xs"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            刷新数据
          </Button>
        </div>
      </div>

      {/* 4个小结指标 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="glass-panel border-border/40 bg-background/20 hover:scale-[1.01] transition-all duration-300 shadow-md">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <Activity className="h-3.5 w-3.5 text-primary" />
              全书情感均分
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <div className="text-2xl font-bold font-mono text-foreground flex items-baseline gap-1">
              {summary ? summary.avg_score.toFixed(3) : "0.500"}
              <span className="text-xs font-normal text-muted-foreground">/1.0</span>
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5">
              整体风格: {summary ? (summary.avg_score >= 0.6 ? "温暖昂扬" : summary.avg_score <= 0.45 ? "深沉压抑" : "平缓叙事") : "暂无数据"}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/40 bg-background/20 hover:scale-[1.01] transition-all duration-300 shadow-md">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <Smile className="h-3.5 w-3.5 text-emerald-400" />
              高潮顶点章节
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <div className="text-xl font-bold text-emerald-400 truncate">
              {summary && summary.max_score_chapter ? `第 ${summary.max_score_chapter} 章` : "暂无"}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5">
              全书情感得分最高点
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/40 bg-background/20 hover:scale-[1.01] transition-all duration-300 shadow-md">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <Frown className="h-3.5 w-3.5 text-red-400" />
              低谷虐心章节
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <div className="text-xl font-bold text-red-400 truncate">
              {summary && summary.min_score_chapter ? `第 ${summary.min_score_chapter} 章` : "暂无"}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5">
              全书情感得分最低谷
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/40 bg-background/20 hover:scale-[1.01] transition-all duration-300 shadow-md">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              分析章节总数
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <div className="text-2xl font-bold font-mono text-foreground">
              {summary ? summary.chapter_count : 0} <span className="text-xs font-normal text-muted-foreground">章</span>
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5">
              占当前总章节的 100%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 图表主区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧折线图 */}
        <Card className="lg:col-span-2 bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Activity className="h-4 w-4 text-emerald-400" />
                  章节情感起伏弧线 (Emotion Arc)
                </CardTitle>
                <CardDescription className="text-xs">
                  X轴代表章节走势，Y轴代表情感积极度。曲线起伏可展现“跌宕起伏”的小说结构张力。
                </CardDescription>
              </div>
              <div className="flex gap-2.5 text-[9px] font-mono text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  积极 (&gt;0.70)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  中性/紧张 (0.40~0.70)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  虐心/消极 (&lt;0.40)
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            {loading ? (
              <div className="space-y-4 py-8">
                <Skeleton className="h-[180px] w-full rounded-xl" />
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
                </div>
              </div>
            ) : (
              renderSvgChart()
            )}
          </CardContent>
        </Card>

        {/* 右侧选中分析面板 */}
        <div className="h-full">
          {loading ? (
            <Skeleton className="h-full min-h-[300px] rounded-xl" />
          ) : (
            renderDetailReport()
          )}
        </div>
      </div>

      {/* 下方两栏：单章深度分析操作 + 快速文本测试 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 单章测试/深度分析 */}
        <Card className="bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Play className="h-4 w-4 text-emerald-400" />
              单章节情感深度重析
            </CardTitle>
            <CardDescription className="text-xs">
              选定小说某特定章节，用指定算法对其进行深度切片分析，获取句级/词级细节数据。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <span className="text-xs text-muted-foreground block mb-1">选择章节：</span>
                <Select value={selectedChapterNum} onValueChange={(val) => setSelectedChapterNum(val || "")}>
                  <SelectTrigger className="w-full h-10 border-border/60 bg-background/40 rounded-xl text-xs">
                    <SelectValue placeholder="选择章节" />
                  </SelectTrigger>
                  <SelectContent>
                    {arcData.length > 0 ? (
                      arcData.map((item) => (
                        <SelectItem key={item.chapter_number} value={String(item.chapter_number)}>
                          {item.title} (当前分: {item.score.toFixed(2)})
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="1">第1章 (默认)</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="self-end">
                <Button
                  onClick={handleAnalyzeSingle}
                  disabled={singleAnalyzing || !selectedChapterNum}
                  className="shadow-md bg-primary text-xs hover:bg-primary/90 rounded-xl h-10"
                >
                  {singleAnalyzing ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      开始重析
                    </>
                  )}
                </Button>
              </div>
            </div>
            
            <div className="text-xs text-muted-foreground flex gap-1 items-start bg-muted/20 border border-border/40 rounded-lg p-2.5">
              <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
              <p>
                建议：若选择“大模型分析”方法，重析通常需要10-20秒以保证对隐喻和微表情的精准捕捉。
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 快速情感测试（论文演示用） */}
        <Card className="bg-background/40 backdrop-blur-md border-border/40 shadow-lg">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              任意文本情感在线测试（科研演示）
            </CardTitle>
            <CardDescription className="text-xs">
              无需读取项目文件，输入任意中文字句段落，实时评估其在词典法/自定义法下的情感分值，利于论文科研数据对比。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={quickText}
              onChange={(e) => setQuickText(e.target.value)}
              placeholder="在此输入需要测试的段落文本（例如：“他走在清晨的朝阳里，心中充满了莫名的期待，脚底也轻快了许多。”）"
              className="min-h-[80px] text-xs leading-relaxed bg-background/30 rounded-xl resize-none"
            />
            
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>方法:</span>
                <Select value={quickMethod} onValueChange={(val) => setQuickMethod(val || "snownlp")}>
                  <SelectTrigger className="w-[110px] h-8 text-[11px] border-border/60 bg-background/40 rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="snownlp">SnowNLP</SelectItem>
                    <SelectItem value="keyword">文学词典</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleQuickTest}
                disabled={quickLoading || !quickText.trim()}
                size="sm"
                className="shadow-sm bg-indigo-600 hover:bg-indigo-700 text-xs rounded-lg"
              >
                {quickLoading ? (
                  <RefreshCw className="h-3 w-3 mr-1.5 animate-spin" />
                ) : (
                  <Send className="h-3 w-3 mr-1.5" />
                )}
                快速测试
              </Button>
            </div>

            {/* 测试结果 */}
            {quickResult && (
              <div className="rounded-xl border border-border/40 p-2.5 bg-muted/40 flex items-center justify-between text-xs transition-all animate-fade-in">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-foreground">测试结果:</span>
                  <Badge className={`text-[10px] font-mono px-1 py-0 h-4 ${getEmotionColor(quickResult.label)}`}>
                    {quickResult.label}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 font-mono font-bold text-foreground">
                  <span>得分: {quickResult.score.toFixed(3)}</span>
                  {getScoreEmoji(quickResult.score)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
