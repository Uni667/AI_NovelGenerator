"use client"

import React, { useState, useEffect, useMemo, useRef } from "react"
import { useProjectContext } from "./ProjectContext"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  Users, Map, Sparkles, RefreshCw, Search, Copy, BookOpen, 
  ChevronLeft, ChevronRight, Play, Pause, AlertCircle, Loader2, Check,
  Heart, Swords, Shield, Scroll, ShieldAlert, GraduationCap, Clapperboard, HelpCircle, Edit, Save, X
} from "lucide-react"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import type { VisualizerCharacter, VisualizerScene, VisualizerEvent, VisualizerData, VisualizerRelationship } from "@/lib/types"
import { CharacterAvatar } from "./CharacterAvatar"
import dynamic from "next/dynamic"

// Import ForceGraph2D dynamically with SSR disabled to prevent Node document is not defined errors
const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d").then((mod) => mod.default),
  { ssr: false }
)

// Reusable custom React virtual scroll grid for 60fps lists with 1000+ items
interface VirtualGridProps<T> {
  items: T[]
  columns: number
  rowHeight: number
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode
}

function VirtualGrid<T>({ items, columns, rowHeight, renderItem }: VirtualGridProps<T>) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [containerHeight, setContainerHeight] = useState(500)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    
    setContainerHeight(el.clientHeight || 500)
    
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height || 500)
      }
    })
    observer.observe(el)
    
    const handleScrollEvent = () => {
      setScrollTop(el.scrollTop)
    }
    el.addEventListener("scroll", handleScrollEvent)
    
    return () => {
      observer.disconnect()
      el.removeEventListener("scroll", handleScrollEvent)
    }
  }, [])

  const totalRows = Math.ceil(items.length / columns)
  const totalHeight = totalRows * rowHeight
  
  const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - 2)
  const endRow = Math.min(totalRows - 1, Math.floor((scrollTop + containerHeight) / rowHeight) + 2)

  const visibleElements: React.ReactNode[] = []
  for (let r = startRow; r <= endRow; r++) {
    for (let c = 0; c < columns; c++) {
      const idx = r * columns + c
      if (idx < items.length) {
        const style: React.CSSProperties = {
          position: "absolute",
          top: r * rowHeight,
          left: `${(c / columns) * 100}%`,
          width: `${(1 / columns) * 100}%`,
          height: rowHeight,
          padding: "6px",
        }
        visibleElements.push(
          <div key={idx} style={style}>
            {renderItem(items[idx], idx, { height: "100%", width: "100%" })}
          </div>
        )
      }
    }
  }

  return (
    <div 
      ref={containerRef} 
      className="flex-1 overflow-y-auto min-h-0 relative w-full pr-1"
      style={{ height: "100%" }}
    >
      <div style={{ height: totalHeight, width: "100%", position: "relative" }}>
        {visibleElements}
      </div>
    </div>
  )
}

export function VisualizerTab() {
  const { projectId, chapters, refetchChapters, setActiveTab } = useProjectContext()
  const { selectedChapterNumber, setSelectedChapterNumber } = useProjectContext().workbench

  const activeChapter = selectedChapterNumber || 1
  const maxChapters = Math.max(chapters?.length || 1, 1)

  // Dataset states
  const [data, setData] = useState<VisualizerData>({
    schemaVersion: 2,
    characters: [],
    scenes: [],
    events: []
  })
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [generatingPromptId, setGeneratingPromptId] = useState<string | null>(null)
  
  // Navigation & filter states
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTabName, setActiveTabName] = useState("roster")
  const [copiedId, setCopiedId] = useState<string | null>(null)
  
  // Custom columns logic for responsive virtualization grid
  const [columns, setColumns] = useState(4)
  useEffect(() => {
    const handleResize = () => {
      const w = window.innerWidth
      if (w < 640) setColumns(1)
      else if (w < 1024) setColumns(2)
      else if (w < 1280) setColumns(3)
      else setColumns(4)
    }
    window.addEventListener("resize", handleResize)
    handleResize()
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  // Drawer selected character states (P2 details drawer loading/error/race condition safe)
  const [selectedCharId, setSelectedCharId] = useState<string | null>(null)
  const [drawerChar, setDrawerChar] = useState<VisualizerCharacter | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [drawerError, setDrawerError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<Partial<VisualizerCharacter>>({})
  const drawerRequestRef = useRef<string | null>(null)

  const [selectedScene, setSelectedScene] = useState<VisualizerScene | null>(null)

  // Storyboard playback
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(2500) // ms

  // Parse error state (P1: backend AI parsing error structured detail)
  const [parseError, setParseError] = useState<{
    code: string;
    message: string;
    stage: 'request' | 'response' | 'parse' | 'validate' | 'save';
    details?: any;
    rawExcerpt?: string;
    retryable: boolean;
  } | null>(null)

  // ForceGraph search/center reference
  const fgRef = useRef<any>(null)

  // Fetch full visualizer dataset
  const fetchVisualData = async (silent = false) => {
    try {
      if (!silent) setLoading(true)
      const res = await api.visualizer.getData(projectId)
      setData(res || { schemaVersion: 2, characters: [], scenes: [], events: [] })
      setParseError(null)
    } catch (err: any) {
      toast.error(err.message || "获取可视化数据失败")
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    fetchVisualData()
  }, [projectId])

  // Storyboard playback simulation effect
  useEffect(() => {
    let timer: any = null
    if (isPlaying) {
      timer = setInterval(() => {
        setSelectedChapterNumber((prev) => {
          if (prev >= maxChapters) {
            setIsPlaying(false)
            return prev
          }
          return prev + 1
        })
      }, playbackSpeed)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [isPlaying, maxChapters, playbackSpeed, setSelectedChapterNumber])

  // P1: Automatically pause storyboard playback when tab switches, project switches, visibility changes, or unmounts
  useEffect(() => {
    if (activeTabName !== "storyboard") {
      setIsPlaying(false)
    }
  }, [activeTabName])

  useEffect(() => {
    setIsPlaying(false)
    setSelectedCharId(null)
    setDrawerChar(null)
  }, [projectId])

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        setIsPlaying(false)
      }
    }
    document.addEventListener("visibilitychange", handleVisibilityChange)
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [])

  // Fetch character details drawer (loading/error & race condition safe)
  useEffect(() => {
    if (!selectedCharId) {
      setDrawerChar(null)
      setIsEditing(false)
      return
    }

    const reqId = Math.random().toString(36).substring(2, 9)
    drawerRequestRef.current = reqId

    setDrawerLoading(true)
    setDrawerError(null)
    setIsEditing(false)

    api.visualizer.getCharacterDetails(projectId, selectedCharId)
      .then((res) => {
        if (drawerRequestRef.current === reqId) {
          setDrawerChar(res)
          setEditForm(res)
        }
      })
      .catch((err: any) => {
        if (drawerRequestRef.current === reqId) {
          setDrawerError(err.message || "获取人物详情失败")
        }
      })
      .finally(() => {
        if (drawerRequestRef.current === reqId) {
          setDrawerLoading(false)
        }
      })
  }, [selectedCharId, projectId])

  // Trigger chapter parsing with structured error detail handling
  const handleAnalyzeChapter = async (targetCh?: number) => {
    const chLabel = targetCh ? `第 ${targetCh} 章` : "全案"
    try {
      setAnalyzing(true)
      setParseError(null)
      toast.loading(`正在对 ${chLabel} 进行小说设定深度解析与画面构思...`, { id: "analyze" })
      const res = await api.visualizer.analyzeChapters(projectId, targetCh)
      toast.success(
        `解析成功！发现 ${res.new_characters_count} 个人物，${res.new_scenes_count} 个场景和 ${res.new_events_count} 个分镜事件。`,
        { id: "analyze" }
      )
      await fetchVisualData(true)
      refetchChapters()
    } catch (err: any) {
      toast.error(err.message || "解析失败", { id: "analyze" })
      if (err.details) {
        setParseError({
          code: err.code || "UNKNOWN",
          message: err.message,
          stage: err.details.stage || "request",
          details: err.details.details,
          rawExcerpt: err.details.rawExcerpt,
          retryable: err.details.retryable ?? true
        })
      } else {
        setParseError({
          code: "UNKNOWN",
          message: err.message || "未知错误",
          stage: "request",
          retryable: true
        })
      }
    } finally {
      setAnalyzing(false)
    }
  }

  // Trigger prompt generation
  const handleGeneratePrompt = async (type: "character" | "scene" | "event", id: string) => {
    setGeneratingPromptId(`${type}_${id}`)
    try {
      const res = await api.visualizer.generatePrompt(projectId, type, id)
      toast.success("画风提示词生成成功")
      await fetchVisualData(true)
      if (type === "character" && selectedCharId === id) {
        setDrawerChar(prev => prev ? { ...prev, avatarPrompt: res.prompt, imageStatus: "prompt_ready" } : null)
        setEditForm(prev => prev ? { ...prev, avatarPrompt: res.prompt, imageStatus: "prompt_ready" } : {})
      }
    } catch (err: any) {
      toast.error(err.message || "生成提示词失败")
    } finally {
      setGeneratingPromptId(null)
    }
  }

  // Avatar generation triggers if feature flag is active
  const handleGenerateAvatarImage = async (charId: string) => {
    setGeneratingPromptId(`image_${charId}`)
    try {
      const res = await api.visualizer.generateAvatar(projectId, charId)
      toast.success("AI 角色卡通头像生成成功！")
      await fetchVisualData(true)
      if (selectedCharId === charId) {
        setDrawerChar(prev => prev ? { ...prev, avatarUrl: res.avatarUrl, imageStatus: "generated" } : null)
      }
    } catch (err: any) {
      toast.error(err.message || "头像生成失败，请确认配置")
    } finally {
      setGeneratingPromptId(null)
    }
  }

  // Save character manual edits and sync to SQLite
  const handleSaveCharacterEdit = async () => {
    if (!drawerChar) return
    try {
      const updated = await api.visualizer.updateCharacter(projectId, drawerChar.id, editForm)
      setDrawerChar(updated)
      setData(prev => ({
        ...prev,
        characters: prev.characters.map(c => c.id === updated.id ? updated : c)
      }))
      setIsEditing(false)
      toast.success("人物设定保存成功")
    } catch (err: any) {
      toast.error(err.message || "保存失败")
    }
  }

  const handleCopyText = (text: string, id: string) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    toast.success("已复制到剪贴板！可粘贴至 SD / Midjourney 绘图")
    setTimeout(() => setCopiedId(null), 2000)
  }

  // P0 & P2 safe chapter workspace redirections without page reload
  const handleChapterJump = (chNum: number) => {
    toast.info(`已切换到第 ${chNum} 章，正在加载写作面板...`)
    setActiveTab("workbench")
    setSelectedChapterNumber(chNum)
    setSelectedCharId(null)
    
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      params.set("tab", "workbench")
      params.set("chapterId", String(chNum))
      params.set("source", "visualizer")
      window.history.pushState(null, "", "?" + params.toString())
    }
  }

  // Filtered dataset mapping
  const filteredCharacters = useMemo(() => {
    return data.characters.filter((c) => {
      const q = searchQuery.toLowerCase()
      return (
        c.name.toLowerCase().includes(q) ||
        (c.identity && c.identity.toLowerCase().includes(q)) ||
        (c.faction && c.faction.toLowerCase().includes(q)) ||
        (c.personalityTags && c.personalityTags.some((tag) => tag.toLowerCase().includes(q)))
      )
    })
  }, [data.characters, searchQuery])

  const filteredEvents = useMemo(() => {
    return data.events.filter((e) => e.chapterId === String(activeChapter))
  }, [data.events, activeChapter])

  // World ForceGraph configuration
  const graphData = useMemo(() => {
    const nodes = data.characters.map(c => ({
      id: c.id,
      name: c.name,
      roleType: c.roleType,
      avatarUrl: c.avatarUrl
    }))
    
    const links: any[] = []
    const seen = new Set<string>()
    
    data.characters.forEach(char => {
      if (char.relationships) {
        char.relationships.forEach(rel => {
          const key = [char.id, rel.targetCharacterId].sort().join("-")
          if (!seen.has(key)) {
            seen.add(key)
            links.push({
              source: char.id,
              target: rel.targetCharacterId,
              relationType: rel.relationType,
              description: rel.description
            })
          }
        })
      }
    })
    
    return { nodes, links }
  }, [data.characters])

  // Center Graph on searched nodes
  const handleGraphSearch = (val: string) => {
    setSearchQuery(val)
    if (!val || !fgRef.current) return
    const matched = graphData.nodes.find(n => n.name.toLowerCase().includes(val.toLowerCase())) as any
    if (matched) {
      fgRef.current.centerAt(matched.x, matched.y, 800)
      fgRef.current.zoom(2.2, 800)
    }
  }

  // Role style badges
  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case "主角": return "bg-violet-500/10 text-violet-400 border-violet-500/20"
      case "女主": return "bg-pink-500/10 text-pink-400 border-pink-500/20"
      case "反派": return "bg-rose-500/10 text-rose-400 border-rose-500/20"
      case "配角": return "bg-blue-500/10 text-blue-400 border-blue-500/20"
      case "NPC": return "bg-slate-500/10 text-slate-400 border-slate-500/20"
      default: return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
    }
  }

  const getGenderEmoji = (gender?: string) => {
    if (gender === "男") return "♂️"
    if (gender === "女") return "♀️"
    return "❓"
  }

  if (loading) {
    return (
      <div className="flex-1 min-h-[400px] flex flex-col items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="text-sm">正在加载小说全景图谱与场景记忆...</span>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 gap-4">
      {/* 顶部工具栏 */}
      <Card className="glass-panel border-border/40 shrink-0 p-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-lg font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
              小说可视化与具象化面板
            </h2>
            <p className="text-xs text-muted-foreground">
              为小说赋予视觉表达：生成萌系角色人物卡、场景记忆氛围、分镜线索，构建可演绎的时空因果图谱。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={analyzing}
              onClick={() => handleAnalyzeChapter(activeChapter)}
              className="border-primary/20 bg-primary/5 text-primary hover:bg-primary/10 h-9 text-xs font-bold"
            >
              {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Sparkles className="h-3.5 w-3.5 mr-1.5 text-primary" />}
              解析当前章(第{activeChapter}章)
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={analyzing}
              onClick={() => handleAnalyzeChapter()}
              className="border-indigo-500/20 bg-indigo-500/5 text-indigo-400 hover:bg-indigo-500/10 h-9 text-xs font-bold"
            >
              {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Scroll className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />}
              解析全部已写章节
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => fetchVisualData()}
              className="border-border/40 bg-card hover:bg-muted/40 h-9 text-xs"
              title="刷新可视化数据"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {/* Structured error panel */}
        {parseError && (
          <div className="mt-3 p-3.5 bg-rose-950/20 border border-rose-500/20 rounded-xl space-y-2 text-xs">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2 text-rose-400 font-bold">
                <AlertCircle className="h-4 w-4" />
                <span>AI 解析错误 (错误码: {parseError.code})</span>
              </div>
              {parseError.retryable && (
                <Button size="xs" onClick={() => handleAnalyzeChapter(activeChapter)} className="h-6 bg-rose-600 hover:bg-rose-500 text-white">
                  重试
                </Button>
              )}
            </div>
            <p className="text-slate-300 font-medium">阶段: {parseError.stage} — {parseError.message}</p>
            {parseError.details && (
              <pre className="p-2 bg-black/40 rounded border border-white/5 text-[10px] text-slate-400 whitespace-pre-wrap font-mono">
                {String(parseError.details)}
              </pre>
            )}
            {parseError.rawExcerpt && (
              <div className="space-y-1">
                <span className="text-[10px] text-muted-foreground font-bold">AI 原始输出截余:</span>
                <pre className="p-2 bg-black/40 rounded border border-white/5 text-[10px] text-slate-400 whitespace-pre-wrap font-mono line-clamp-3">
                  {parseError.rawExcerpt}
                </pre>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* 主体切换面板 */}
      <Tabs value={activeTabName} onValueChange={setActiveTabName} className="flex-1 flex flex-col min-h-0 gap-4">
        <TabsList className="bg-background/40 backdrop-blur-md border border-border/40 p-1 flex justify-start gap-1 rounded-xl w-full shrink-0">
          <TabsTrigger value="roster" className="rounded-lg px-4 py-2 text-xs shrink-0 data-[state=active]:bg-primary/25">
            <Users className="h-3.5 w-3.5 mr-1.5 text-violet-400" />
            人物图鉴 ({data.characters.length})
          </TabsTrigger>
          <TabsTrigger value="gallery" className="rounded-lg px-4 py-2 text-xs shrink-0 data-[state=active]:bg-primary/25">
            <Map className="h-3.5 w-3.5 mr-1.5 text-emerald-400" />
            场景画廊 ({data.scenes.length})
          </TabsTrigger>
          <TabsTrigger value="storyboard" className="rounded-lg px-4 py-2 text-xs shrink-0 data-[state=active]:bg-primary/25">
            <Clapperboard className="h-3.5 w-3.5 mr-1.5 text-amber-400" />
            剧情分镜 ({data.events.length})
          </TabsTrigger>
          <TabsTrigger value="relations" className="rounded-lg px-4 py-2 text-xs shrink-0 data-[state=active]:bg-primary/25">
            <HelpCircle className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
            世界关系图
          </TabsTrigger>
        </TabsList>

        {/* 1. 人物图鉴 */}
        <TabsContent value="roster" className="flex-1 flex flex-col min-h-0 outline-none gap-4">
          <div className="flex items-center gap-2 shrink-0">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="按照角色姓名、势力、性格标签或身份进行检索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-card border-border/40 focus:border-primary/40 text-xs h-9 rounded-xl"
              />
            </div>
            {searchQuery && (
              <Button size="sm" variant="ghost" onClick={() => setSearchQuery("")} className="text-xs shrink-0">
                清除筛选
              </Button>
            )}
          </div>

          {filteredCharacters.length === 0 ? (
            <div className="flex-1 border border-dashed border-border/40 rounded-2xl flex flex-col items-center justify-center p-12 text-center bg-card/5">
              <AlertCircle className="h-10 w-10 text-indigo-400/50 mb-3" />
              <h3 className="text-sm font-bold text-slate-200">没有找到人物数据</h3>
              <p className="text-xs text-muted-foreground mt-2 max-w-sm leading-relaxed">
                {data.characters.length === 0 
                  ? "当前小说尚未解析出任何角色。请在右上方点击「解析当前章」或「解析全部已写章节」进行提取。"
                  : "没有找到与您的检索关键词相匹配的已有人物设定。"}
              </p>
            </div>
          ) : (
            <VirtualGrid
              items={filteredCharacters}
              columns={columns}
              rowHeight={420}
              renderItem={(char, index, style) => (
                <Card
                  style={style}
                  className="glass-card border-border/40 overflow-hidden flex flex-col hover:border-violet-500/20 transition-all duration-300"
                >
                  <div className="relative w-full aspect-[3/4] bg-gradient-to-br from-violet-900/20 to-indigo-950/20 border-b border-white/5 flex flex-col items-center justify-center p-4 gap-2">
                    <CharacterAvatar
                      character={char}
                      size="xl"
                      className="ring-2 ring-violet-500/20"
                    />
                    <h3 className="text-sm font-bold text-slate-200 text-center">{char.name}</h3>
                    {char.aliases && char.aliases.length > 0 && (
                      <p className="text-[10px] text-muted-foreground text-center">{char.aliases.join(" / ")}</p>
                    )}
                    <Badge className="text-[9px] bg-violet-500/10 text-violet-300 border-violet-500/20">{char.roleType}</Badge>
                    {char.faction && (
                      <span className="text-[10px] text-muted-foreground">{char.faction}</span>
                    )}
                  </div>
                  <CardContent className="p-4 flex-1 flex flex-col justify-between gap-3">
                    <div className="space-y-2">
                      {char.personalityTags && char.personalityTags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {char.personalityTags.slice(0, 4).map((tag, i) => (
                            <span key={i} className="text-[8px] bg-white/5 px-1.5 py-0.5 rounded border border-white/5 text-slate-300">{tag}</span>
                          ))}
                        </div>
                      )}
                      <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed">
                        {char.appearance || "暂无简介"}
                      </p>
                    </div>
                    <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/5">
                      <span>出场: 第 {char.firstChapterId} 章</span>
                      <Button
                        variant="link"
                        size="xs"
                        onClick={() => setSelectedCharId(char.id)}
                        className="h-5 px-1.5 text-violet-400 hover:text-violet-300 font-bold"
                      >
                        查看详情
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            />
          )}
        </TabsContent>

        {/* 2. 场景画廊 */}
        <TabsContent value="gallery" className="flex-1 flex flex-col min-h-0 outline-none">
          {data.scenes.length === 0 ? (
            <div className="flex-1 border border-dashed border-border/40 rounded-2xl flex flex-col items-center justify-center p-12 text-center bg-card/5">
              <Map className="h-10 w-10 text-emerald-400/50 mb-3" />
              <h3 className="text-sm font-bold text-slate-200">没有场景数据</h3>
              <p className="text-xs text-muted-foreground mt-2 max-w-sm leading-relaxed">
                当前小说尚未提取出环境、房间或地图节点。请解析章节正文以生成场景画廊。
              </p>
            </div>
          ) : (
            <VirtualGrid
              items={data.scenes}
              columns={columns > 2 ? 3 : columns}
              rowHeight={340}
              renderItem={(scene, index, style) => (
                <Card 
                  style={style}
                  className="glass-card border-border/40 overflow-hidden flex flex-col hover:border-emerald-500/20 transition-all duration-300"
                >
                  <div className="relative w-full aspect-video bg-gradient-to-br from-teal-900/20 to-emerald-950/20 border-b border-white/5 flex flex-col items-center justify-center p-4">
                    <Map className="h-10 w-10 text-emerald-400/40 mb-1" />
                    <span className="text-[10px] text-muted-foreground font-mono bg-black/40 px-2 py-0.5 rounded border border-white/5 mb-8">
                      📍 {scene.type}
                    </span>
                    
                    <div className="absolute bottom-2 left-2 right-2">
                      {scene.imagePrompt ? (
                        <div className="bg-slate-950/90 backdrop-blur-md p-2 rounded-lg border border-white/5 space-y-1">
                          <span className="text-[9px] font-bold text-emerald-400 block uppercase tracking-wide">
                            🖼️ 场景氛围绘图 Prompt
                          </span>
                          <p className="text-[10px] text-slate-300 line-clamp-2 leading-tight font-mono">
                            {scene.imagePrompt}
                          </p>
                          <div className="flex justify-between items-center pt-1 border-t border-white/5">
                            <span className="text-[8px] text-muted-foreground">
                              SD提示词就绪
                            </span>
                            <Button 
                              size="xs" 
                              variant="ghost" 
                              className="h-5 px-1.5 text-[9px] hover:bg-white/10"
                              onClick={() => handleCopyText(scene.imagePrompt || "", `scene_${scene.id}`)}
                            >
                              {copiedId === `scene_${scene.id}` ? <Check className="h-3 w-3 mr-1 text-emerald-400" /> : <Copy className="h-3 w-3 mr-1" />}
                              复制
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <Button 
                          size="xs" 
                          className="w-full bg-slate-950/80 hover:bg-slate-900 border border-white/5 text-[9px] h-7"
                          onClick={() => handleGeneratePrompt("scene", scene.id)}
                          disabled={generatingPromptId === `scene_${scene.id}`}
                        >
                          {generatingPromptId === `scene_${scene.id}` ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sparkles className="h-3 w-3 mr-1 text-emerald-400" />}
                          生成场景概念图提示词
                        </Button>
                      )}
                    </div>
                  </div>

                  <CardContent className="p-4 flex-1 flex flex-col justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-sm text-slate-200">{scene.name}</span>
                        <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px]">
                          {scene.atmosphere}
                        </Badge>
                      </div>

                      <p className="text-xs text-[#A3A3C2] leading-relaxed line-clamp-2">
                        {scene.description || "暂无场景描述详情，解析相应章节后可完善细节。"}
                      </p>
                    </div>

                    <div className="border-t border-border/20 pt-2 space-y-2 text-[10px] text-muted-foreground">
                      <div className="flex flex-wrap items-center gap-1">
                        <span>关联演员:</span>
                        {scene.characterIds.length === 0 ? (
                          <span className="italic text-muted-foreground">无</span>
                        ) : (
                          scene.characterIds.map((charId) => {
                            const name = data.characters.find(c => c.id === charId)?.name || charId
                            return (
                              <Badge key={charId} variant="secondary" className="bg-slate-800 text-[#A3A3C2] text-[9px] h-4 cursor-pointer hover:bg-slate-700" onClick={() => setSelectedCharId(charId)}>
                                {name}
                              </Badge>
                            )
                          })
                        )}
                      </div>
                      <div className="flex items-center justify-between font-medium">
                        <span>关联章节: 第 {scene.relatedChapterIds.join(", ")} 章</span>
                        <Button 
                          variant="ghost" 
                          size="xs" 
                          onClick={() => setSelectedScene(scene)}
                          className="h-5 px-1.5 text-emerald-400 hover:text-emerald-300 font-bold hover:bg-emerald-500/10"
                        >
                          查看详情
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            />
          )}
        </TabsContent>

        {/* 3. 剧情分镜 */}
        <TabsContent value="storyboard" className="flex-1 flex flex-col min-h-0 outline-none gap-4">
          <Card className="glass-panel border-border/40 shrink-0 p-3 flex flex-col gap-2 bg-[#0b0f1a]/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-amber-500/20 bg-amber-500/10 text-amber-400 px-2.5 py-0.5 text-[10px]">
                  分镜放映室
                </Badge>
                <h2 className="text-sm font-semibold text-foreground">
                  第 {activeChapter}/{maxChapters} 章: {chapters?.find(c => c.chapter_number === activeChapter)?.chapter_title || "未命名"}
                </h2>
              </div>

              <div className="flex items-center gap-1.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  disabled={activeChapter <= 1}
                  onClick={() => {
                    setIsPlaying(false)
                    setSelectedChapterNumber(activeChapter - 1)
                  }}
                  title="上一章"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 px-3 text-xs flex items-center gap-1.5 border-border/40 bg-card hover:bg-muted/40 cursor-pointer"
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? (
                    <><Pause className="h-3.5 w-3.5 text-amber-500 fill-current animate-pulse" /> 暂停放映</>
                  ) : (
                    <><Play className="h-3.5 w-3.5 text-emerald-500 fill-current" /> 自动放映</>
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  disabled={activeChapter >= maxChapters}
                  onClick={() => {
                    setIsPlaying(false)
                    setSelectedChapterNumber(activeChapter + 1)
                  }}
                  title="下一章"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none border-t border-white/5 pt-2 mt-1">
              {Array.from({ length: maxChapters }, (_, i) => i + 1).map((chNum) => {
                const isActive = chNum === activeChapter
                const hasEvent = data.events.some((e) => e.chapterId === String(chNum))
                const meta = chapters?.find(c => c.chapter_number === chNum)

                return (
                  <button
                    key={chNum}
                    type="button"
                    onClick={() => {
                      setIsPlaying(false)
                      setSelectedChapterNumber(chNum)
                    }}
                    className={`flex-none w-10 h-10 rounded-xl border flex flex-col items-center justify-center transition-all cursor-pointer relative ${
                      isActive
                        ? "bg-amber-500 border-amber-500 text-slate-950 font-bold scale-105 shadow-md shadow-amber-500/20"
                        : hasEvent
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20"
                        : "bg-slate-900/40 border-white/5 text-slate-500 hover:bg-slate-800/40 hover:text-slate-300"
                    }`}
                    title={`第 ${chNum} 章: ${meta?.chapter_title || "未命名"}`}
                  >
                    <span className="text-[11px] font-mono leading-none">{chNum}</span>
                    {hasEvent && !isActive && (
                      <span className="absolute bottom-1 right-1 h-1.5 w-1.5 rounded-full bg-amber-400" />
                    )}
                  </button>
                )
              })}
            </div>
          </Card>

          {filteredEvents.length === 0 ? (
            <div className="flex-1 border border-dashed border-border/40 rounded-2xl flex flex-col items-center justify-center p-12 text-center bg-card/5">
              <Clapperboard className="h-10 w-10 text-amber-400/50 mb-3" />
              <h3 className="text-sm font-bold text-slate-200">第 {activeChapter} 章没有分镜事件</h3>
              <p className="text-xs text-muted-foreground mt-2 max-w-sm leading-relaxed font-semibold">
                当前章节尚未解析出分镜。请在页面顶部点击「解析当前章」提取分镜。
              </p>
              <Button onClick={() => handleChapterJump(activeChapter)} className="mt-4 text-xs bg-indigo-600 hover:bg-indigo-500 font-bold h-8">
                <BookOpen className="h-3.5 w-3.5 mr-1" /> 前往写作该章
              </Button>
            </div>
          ) : (
            <div className="flex-1 flex flex-col min-h-0 gap-4">
              <VirtualGrid
                items={filteredEvents}
                columns={1}
                rowHeight={280}
                renderItem={(event, idx) => {
                  const scene = data.scenes.find(s => s.id === event.sceneId)
                  
                  return (
                    <div 
                      className="border border-border/40 rounded-2xl bg-slate-950/40 flex flex-col sm:flex-row overflow-hidden hover:border-amber-500/20 transition-all duration-300 h-full"
                    >
                      <div className="relative w-full sm:w-64 aspect-video sm:aspect-auto bg-gradient-to-br from-indigo-950/20 to-slate-900 flex flex-col items-center justify-center p-4 border-r border-white/5 shrink-0">
                        <span className="absolute top-2 left-2 bg-amber-500 text-slate-950 text-[10px] font-bold px-2 py-0.5 rounded-md">
                          SHOT #{idx + 1}
                        </span>
                        {scene && (
                          <span className="absolute top-2 right-2 bg-slate-800 text-[9px] text-[#A3A3C2] border border-white/5 px-2 py-0.5 rounded-md">
                            📍 {scene.name}
                          </span>
                        )}
                        
                        <Clapperboard className="h-10 w-10 text-amber-400/30 mb-2 mt-4" />
                        
                        <div className="absolute bottom-2 left-2 right-2">
                          {event.storyboardPrompt ? (
                            <div className="bg-slate-950/95 backdrop-blur-md p-2 rounded-lg border border-white/5 space-y-1">
                              <span className="text-[8px] font-bold text-amber-400 block uppercase tracking-wide">
                                🎬 导演分镜 Prompt
                              </span>
                              <p className="text-[9px] text-slate-300 line-clamp-2 leading-tight font-mono">
                                {event.storyboardPrompt}
                              </p>
                              <div className="flex justify-between items-center pt-1 border-t border-white/5">
                                <span className="text-[8px] text-muted-foreground">
                                  storyboard prompt
                                </span>
                                <Button 
                                  size="xs" 
                                  variant="ghost" 
                                  className="h-5 px-1.5 text-[8px] hover:bg-white/10"
                                  onClick={() => handleCopyText(event.storyboardPrompt || "", `event_${event.id}`)}
                                >
                                  {copiedId === `event_${event.id}` ? <Check className="h-3 w-3 mr-1 text-emerald-400" /> : <Copy className="h-3 w-3 mr-1" />}
                                  复制
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <Button 
                              size="xs" 
                              className="w-full bg-slate-950/80 hover:bg-slate-900 border border-white/5 text-[9px] h-7"
                              onClick={() => handleGeneratePrompt("event", event.id)}
                              disabled={generatingPromptId === `event_${event.id}`}
                            >
                              {generatingPromptId === `event_${event.id}` ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sparkles className="h-3 w-3 mr-1 text-amber-400" />}
                              生成此镜提示词
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="p-4 flex-1 flex flex-col justify-between gap-3 min-w-0">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sm text-slate-200 truncate">{event.title}</span>
                            <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[9px]">
                              {event.mood}
                            </Badge>
                          </div>
                          <p className="text-xs text-[#A3A3C2] leading-relaxed line-clamp-3">
                            {event.summary}
                          </p>
                        </div>

                        <div className="border-t border-white/5 pt-2 text-[10px] space-y-1.5 text-muted-foreground">
                          <div className="flex flex-wrap gap-1 items-center">
                            <span>出场角色:</span>
                            {event.characterIds.map((charId) => {
                              const charObj = data.characters.find(c => c.id === charId)
                              const charName = charObj ? charObj.name : charId
                              return (
                                <Badge key={charId} variant="secondary" className="bg-slate-900 text-slate-300 text-[8px] h-4 cursor-pointer hover:bg-slate-800" onClick={() => setSelectedCharId(charId)}>
                                  {charName}
                                </Badge>
                              )
                            })}
                          </div>
                          {event.consequences && (
                            <div className="bg-amber-500/5 border border-amber-500/10 p-2 rounded-lg text-amber-300/85">
                              <span className="font-semibold text-[9px] block">🔍 因果蝴蝶效应:</span>
                              {event.consequences}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                }}
              />
              <div className="flex justify-end p-2 shrink-0">
                <Button onClick={() => handleChapterJump(activeChapter)} className="h-8 text-xs bg-indigo-600 hover:bg-indigo-500 font-bold">
                  前往改写正文
                </Button>
              </div>
            </div>
          )}
        </TabsContent>

        {/* 4. 世界关系图 */}
        <TabsContent value="relations" className="flex-1 flex flex-col min-h-0 outline-none">
          {data.characters.length === 0 ? (
            <div className="flex-1 border border-dashed border-border/40 rounded-2xl flex flex-col items-center justify-center p-12 text-center bg-card/5">
              <HelpCircle className="h-10 w-10 text-indigo-400/50 mb-3" />
              <h3 className="text-sm font-bold text-slate-200">没有关系图数据</h3>
              <p className="text-xs text-muted-foreground mt-2 max-w-sm leading-relaxed">
                当前项目尚未提取人物设定与关系图谱，无法生成关系网结构。请先解析章节正文。
              </p>
            </div>
          ) : (
            <Card className="glass-panel border-border/40 flex-1 relative overflow-hidden bg-[#05070d]/50 p-4">
              <div className="absolute top-4 left-4 z-10 max-w-xs bg-slate-950/80 p-3 rounded-xl border border-white/5 space-y-1.5 backdrop-blur-md">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wide">
                  世界人物图谱 (Force Graph)
                </span>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  使用 D3 力导向算法渲染的交互式人物关系网。按住拖拽节点可改变布局，滚动滚轮可缩放视野。
                </p>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input 
                    placeholder="在图中搜索人物并高亮..." 
                    value={searchQuery}
                    onChange={(e) => handleGraphSearch(e.target.value)}
                    className="pl-8 bg-black/60 border-white/5 text-[10px] h-7 rounded"
                  />
                </div>
              </div>

              {/* Force Directed Graph Canvas */}
              <div className="w-full h-full min-h-[420px] flex items-center justify-center">
                <ForceGraph2D
                  ref={fgRef}
                  graphData={graphData}
                  nodeLabel="name"
                  backgroundColor="#05070d"
                  linkColor={() => "rgba(99, 102, 241, 0.25)"}
                  linkWidth={1.5}
                  linkDirectionalParticles={2}
                  linkDirectionalParticleSpeed={0.005}
                  linkDirectionalParticleWidth={1.5}
                  onNodeClick={(node: any) => {
                    setSelectedCharId(node.id)
                  }}
                  nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                    const label = node.name
                    const radius = 8
                    const isSelected = selectedCharId === node.id
                    const isSearched = searchQuery && node.name.toLowerCase().includes(searchQuery.toLowerCase())
                    
                    // Outer circle boundary
                    ctx.beginPath()
                    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false)
                    
                    let col = "#475569" // default slate
                    if (node.roleType === "主角") col = "#8b5cf6"
                    else if (node.roleType === "女主") col = "#ec4899"
                    else if (node.roleType === "反派") col = "#ef4444"
                    else if (node.roleType === "配角") col = "#3b82f6"
                    
                    ctx.fillStyle = col
                    ctx.fill()
                    
                    // Highlight selected or searched
                    ctx.strokeStyle = isSelected || isSearched ? "#f59e0b" : "#ffffff"
                    ctx.lineWidth = isSelected || isSearched ? 2.5 : 1
                    ctx.stroke()
                    
                    // Node text content (Initials inside circle if scale is high)
                    if (globalScale > 1.8) {
                      ctx.font = `bold ${8 / globalScale}px sans-serif`
                      ctx.textAlign = "center"
                      ctx.textBaseline = "middle"
                      ctx.fillStyle = "#ffffff"
                      ctx.fillText(label.slice(0, 1), node.x, node.y)
                    }
                    
                    // Label text below node
                    const textY = node.y + radius + (11 / globalScale)
                    ctx.font = `${10 / globalScale}px sans-serif`
                    ctx.textAlign = "center"
                    ctx.textBaseline = "middle"
                    ctx.fillStyle = isSelected || isSearched ? "#f59e0b" : "#94a3b8"
                    ctx.fillText(label, node.x, textY)
                  }}
                  onEngineStop={() => {
                    // Prevent memory leak by letting simulation settle
                  }}
                />
              </div>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* 5. 角色详情抽屉 (Race-condition safe loading/error, clickable relation, and editing) */}
      {selectedCharId && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setSelectedCharId(null)}>
          <div 
            className="w-full max-w-md bg-[#0b0f1a] border-l border-white/5 h-full flex flex-col p-6 overflow-y-auto space-y-5 shadow-2xl relative animate-in slide-in-from-right duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close trigger */}
            <button 
              type="button" 
              onClick={() => setSelectedCharId(null)} 
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 font-bold text-lg cursor-pointer"
            >
              ✕
            </button>

            {drawerLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span>正在加载人物深度设定...</span>
              </div>
            ) : drawerError ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-4">
                <AlertCircle className="h-10 w-10 text-rose-500" />
                <p className="text-sm font-semibold text-slate-200">{drawerError}</p>
                <Button size="sm" onClick={() => setSelectedCharId(selectedCharId)} className="bg-primary hover:bg-primary/80">
                  重试
                </Button>
              </div>
            ) : drawerChar ? (
              <>
                {/* Header */}
                <div className="flex items-center justify-between border-b border-white/5 pb-3">
                  <div className="flex items-center gap-3">
                    <CharacterAvatar character={drawerChar} size="lg" />
                    <div>
                      {isEditing ? (
                        <Input 
                          value={editForm.name || ""} 
                          onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                          className="h-8 bg-card text-sm font-bold w-32 border-white/10"
                        />
                      ) : (
                        <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                          {drawerChar.name}
                          {drawerChar.isUnconfirmed && (
                            <Badge variant="outline" className="border-amber-500/30 text-amber-500 bg-amber-500/5 text-[8px] h-4">待确认</Badge>
                          )}
                        </h3>
                      )}
                      
                      <div className="flex flex-wrap gap-1.5 items-center mt-1 text-[10px] text-muted-foreground">
                        <span>{getGenderEmoji(drawerChar.gender)} {drawerChar.gender}</span>
                        <span>•</span>
                        <span>{drawerChar.age}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {isEditing ? (
                      <>
                        <Button size="xs" variant="outline" onClick={() => setIsEditing(false)} className="h-7 text-[10px]">
                          <X className="h-3 w-3 mr-1" />取消
                        </Button>
                        <Button size="xs" onClick={handleSaveCharacterEdit} className="h-7 text-[10px] bg-emerald-600 hover:bg-emerald-500">
                          <Save className="h-3 w-3 mr-1" />保存
                        </Button>
                      </>
                    ) : (
                      <Button size="xs" variant="outline" onClick={() => setIsEditing(true)} className="h-7 text-[10px] border-white/5">
                        <Edit className="h-3 w-3 mr-1" />修改设定
                      </Button>
                    )}
                  </div>
                </div>

                {/* Edit Form / Render View */}
                {isEditing ? (
                  <div className="space-y-4 text-xs pr-1">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground font-bold uppercase">角色定位</label>
                        <Select 
                          value={editForm.roleType || "未知"} 
                          onValueChange={(val) => setEditForm({ ...editForm, roleType: val as any })}
                        >
                          <SelectTrigger className="h-8 bg-card text-xs border-white/10">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-900 text-slate-200">
                            <SelectItem value="主角">主角</SelectItem>
                            <SelectItem value="女主">女主</SelectItem>
                            <SelectItem value="配角">配角</SelectItem>
                            <SelectItem value="反派">反派</SelectItem>
                            <SelectItem value="NPC">NPC</SelectItem>
                            <SelectItem value="未知">未知</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground font-bold uppercase">阵营势力</label>
                        <Input 
                          value={editForm.faction || ""} 
                          onChange={(e) => setEditForm({ ...editForm, faction: e.target.value })}
                          className="h-8 bg-card border-white/10 text-xs"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground font-bold uppercase">别名(Aliases, 逗号分隔)</label>
                        <Input 
                          value={(editForm.aliases || []).join(", ")} 
                          onChange={(e) => setEditForm({ ...editForm, aliases: e.target.value.split(",").map(a => a.trim()).filter(Boolean) })}
                          className="h-8 bg-card border-white/10 text-xs"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground font-bold uppercase">身份职业</label>
                        <Input 
                          value={editForm.identity || ""} 
                          onChange={(e) => setEditForm({ ...editForm, identity: e.target.value })}
                          className="h-8 bg-card border-white/10 text-xs"
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-muted-foreground font-bold uppercase">外貌与衣着描写</label>
                      <Textarea 
                        value={editForm.appearance || ""} 
                        onChange={(e) => setEditForm({ ...editForm, appearance: e.target.value })}
                        className="bg-card border-white/10 text-xs min-h-[60px]"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-muted-foreground font-bold uppercase">性格与去向处境</label>
                      <Textarea 
                        value={editForm.currentStatus || ""} 
                        onChange={(e) => setEditForm({ ...editForm, currentStatus: e.target.value })}
                        className="bg-card border-white/10 text-xs min-h-[60px]"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4 text-xs pr-1 flex-1 overflow-y-auto">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">所属势力</span>
                        <p className="font-semibold text-slate-200 mt-0.5">{drawerChar.faction || "未知"}</p>
                      </div>
                      <div>
                        <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">身份/角色定位</span>
                        <p className="font-semibold text-slate-200 mt-0.5">{drawerChar.identity} · {drawerChar.roleType}</p>
                      </div>
                    </div>

                    {drawerChar.aliases && drawerChar.aliases.length > 0 && (
                      <div>
                        <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">角色别称/外号</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {drawerChar.aliases.map(a => <Badge key={a} variant="secondary" className="bg-slate-800 text-[10px]">{a}</Badge>)}
                        </div>
                      </div>
                    )}

                    <div className="space-y-1">
                      <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">性格特征</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {drawerChar.personalityTags.length === 0 ? (
                          <span className="text-muted-foreground italic">未解析性格特征</span>
                        ) : (
                          drawerChar.personalityTags.map(tag => (
                            <Badge key={tag} className="bg-violet-950/40 text-violet-300 border border-violet-500/10 text-[9px]">{tag}</Badge>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">特殊法宝/功法技能</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {drawerChar.abilities.length === 0 ? (
                          <span className="text-muted-foreground italic">无记录</span>
                        ) : (
                          drawerChar.abilities.map(ab => (
                            <Badge key={ab} className="bg-indigo-950/40 text-indigo-300 border border-indigo-500/10 text-[9px]">{ab}</Badge>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="space-y-1.5 leading-relaxed bg-black/30 border border-white/5 p-3 rounded-xl">
                      <span className="text-[9px] text-indigo-400 font-bold uppercase tracking-wider block">外貌细节样貌描述</span>
                      <p className="text-slate-200">{drawerChar.appearance || "暂无外貌描写"}</p>
                    </div>

                    <div className="space-y-1.5 leading-relaxed bg-black/30 border border-white/5 p-3 rounded-xl">
                      <span className="text-[9px] text-amber-400 font-bold uppercase tracking-wider block">本章时空状态/去向</span>
                      <p className="text-slate-200">{drawerChar.currentStatus || "处于当前时空中活动"}</p>
                    </div>

                    {/* CLICKABLE APPEARANCE JUMP */}
                    <div className="space-y-2">
                      <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">关联章节</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {drawerChar.relatedChapterIds.map(chId => (
                          <Button 
                            key={chId} 
                            variant="secondary"
                            size="xs" 
                            className="bg-slate-900 border border-white/5 text-[9px] h-6 hover:bg-indigo-600 hover:text-white"
                            onClick={() => handleChapterJump(parseInt(chId, 10))}
                          >
                            第 {chId} 章 🔗
                          </Button>
                        ))}
                      </div>
                    </div>

                    {/* CLICKABLE RELATIONDrawer Jumps */}
                    <div className="space-y-3 pt-2">
                      <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider block">
                        人际关网图 ({drawerChar.relationships.length})
                      </span>
                      <div className="space-y-1.5">
                        {drawerChar.relationships.length === 0 ? (
                          <p className="italic text-muted-foreground text-[11px]">尚未建立人际关链。</p>
                        ) : (
                          drawerChar.relationships.map((rel, idx) => {
                            const targetChar = data.characters.find(c => c.id === rel.targetCharacterId)
                            const nameToShow = targetChar ? targetChar.name : "未知角色"
                            
                            return (
                              <div 
                                key={idx}
                                onClick={() => {
                                  if (targetChar) {
                                    setSelectedCharId(targetChar.id)
                                  } else {
                                    toast.error("目标角色不存在或已被删除")
                                  }
                                }}
                                className="flex items-center justify-between p-2 rounded-lg bg-black/20 border border-white/5 cursor-pointer hover:bg-indigo-950/20 hover:border-indigo-500/20 transition-all"
                              >
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-slate-200 text-xs">👤 {nameToShow}</span>
                                  <Badge variant="outline" className={`text-[8px] h-4 ${rel.relationType === '敌对' ? 'bg-rose-500/10 text-rose-400' : 'bg-indigo-500/10 text-indigo-400'}`}>
                                    {rel.relationType}
                                  </Badge>
                                </div>
                                <span className="text-muted-foreground text-[10px] truncate max-w-[180px]">{rel.description}</span>
                              </div>
                            )
                          })
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : null}

            <Button 
              variant="outline" 
              className="w-full text-xs border-white/5 hover:bg-white/5 mt-auto" 
              onClick={() => setSelectedCharId(null)}
            >
              关闭详情
            </Button>
          </div>
        </div>
      )}

      {/* 6. 场景详情对话框 */}
      {selectedScene && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={() => setSelectedScene(null)}>
          <Card 
            className="glass-panel border-border/40 w-full max-w-lg overflow-hidden relative animate-in zoom-in duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              type="button" 
              onClick={() => setSelectedScene(null)} 
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 font-bold text-lg cursor-pointer z-10"
            >
              ✕
            </button>

            <div className="relative aspect-video bg-gradient-to-br from-teal-900/10 to-indigo-950 flex flex-col items-center justify-center p-6 border-b border-white/5">
              <Map className="h-12 w-12 text-emerald-400/40 mb-2" />
              <span className="text-xs text-muted-foreground bg-black/50 border border-white/5 px-2.5 py-0.5 rounded-full backdrop-blur-sm">
                📍 {selectedScene.name} · {selectedScene.type}
              </span>
            </div>

            <CardContent className="p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <h3 className="font-bold text-slate-200 flex items-center gap-1.5">
                  🏮 场景氛围: <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">{selectedScene.atmosphere}</Badge>
                </h3>
                <span className="text-[10px] text-muted-foreground">出现章节: 第 {selectedScene.relatedChapterIds.join(", ")} 章</span>
              </div>

              <div className="space-y-1.5 leading-relaxed text-xs">
                <span className="text-[10px] text-muted-foreground font-bold tracking-wide block uppercase">
                  空间环境描写
                </span>
                <p className="bg-black/30 border border-white/5 p-3 rounded-xl text-slate-200">
                  {selectedScene.description}
                </p>
              </div>

              {selectedScene.imagePrompt && (
                <div className="bg-[#101424] border border-white/5 rounded-2xl p-4 space-y-2">
                  <span className="text-[10px] text-muted-foreground font-bold tracking-wide block uppercase">
                    场景氛围提示词
                  </span>
                  <p className="text-xs text-slate-300 font-mono bg-black/40 p-3 rounded-xl border border-white/5 leading-relaxed break-words">
                    {selectedScene.imagePrompt}
                  </p>
                  <Button 
                    size="sm" 
                    className="w-full text-xs"
                    onClick={() => handleCopyText(selectedScene.imagePrompt || "", `dialog_scene_${selectedScene.id}`)}
                  >
                    {copiedId === `dialog_scene_${selectedScene.id}` ? <Check className="h-3.5 w-3.5 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                    复制场景绘图提示词
                  </Button>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <Button 
                  variant="outline" 
                  className="w-24 text-xs border-white/5 hover:bg-white/5" 
                  onClick={() => setSelectedScene(null)}
                >
                  关闭
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
