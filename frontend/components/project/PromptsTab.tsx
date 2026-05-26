"use client"

import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { useProjectContext } from "@/components/project/ProjectContext"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card } from "@/components/ui/card"
import { 
  Loader2, 
  RefreshCcw, 
  Save, 
  AlertTriangle, 
  GitCompare, 
  History, 
  Download, 
  Upload, 
  X,
  CheckCircle2,
  FileCode
} from "lucide-react"
import { toast } from "sonner"
import type { PromptEntry } from "@/lib/types"

// 变量白名单配置
const PROMPT_ALLOWED_VARIABLES: Record<string, string[]> = {
  core_seed_prompt: ["topic", "genre", "category", "number_of_chapters", "word_number", "user_guidance", "knowledge_context"],
  character_dynamics_prompt: ["core_seed", "user_guidance"],
  world_building_prompt: ["core_seed", "user_guidance"],
  plot_architecture_prompt: ["core_seed", "user_guidance"],
  initial_global_summary_prompt: ["core_seed", "character_dynamics", "world_building", "plot_architecture"],
  initial_plot_arcs_prompt: ["core_seed", "character_dynamics", "world_building", "plot_architecture"],
  create_character_state_prompt: ["core_seed", "characters_involved"],
  architecture_section_polish_prompt: ["platform", "role", "content"],
  chapter_blueprint_prompt: ["novel_setting", "number_of_chapters", "user_guidance"],
  chunked_chapter_blueprint_prompt: ["novel_setting", "current_blueprint", "start_chapter", "end_chapter", "user_guidance"],
  blueprint_polish_prompt: ["novel_setting", "blueprint", "user_guidance"],
  first_chapter_draft_prompt: ["novel_number", "word_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", "characters_involved", "key_items", "scene_location", "time_constraint", "user_guidance", "novel_setting", "plot_arcs", "graph_context", "platform_guidance"],
  next_chapter_draft_prompt: ["global_summary", "previous_chapter_excerpt", "user_guidance", "character_state", "plot_arcs", "graph_context", "short_summary", "platform_guidance", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", "word_number", "characters_involved", "key_items", "scene_location", "time_constraint", "next_chapter_number", "next_chapter_title", "next_chapter_role", "next_chapter_purpose", "next_chapter_suspense_level", "next_chapter_foreshadowing", "next_chapter_plot_twist_level", "next_chapter_summary", "filtered_context"],
  platform_chapter_guidance_prompt: ["platform_label", "platform_rules"],
  summarize_recent_chapters_prompt: ["combined_text", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", "next_chapter_number", "next_chapter_title", "next_chapter_role", "next_chapter_purpose", "next_chapter_summary", "next_chapter_suspense_level", "next_chapter_foreshadowing", "next_chapter_plot_twist_level"],
  de_ai_style_revision_prompt: ["platform_label", "platform_rules", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", "word_number", "chapter_text"],
  chapter_quality_rewrite_prompt: ["platform_label", "platform_rules", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", "opening_feedback", "ending_feedback", "chapter_text"],
  mid_section_quality_prompt: ["chapter_text"],
  dialogue_voice_check_prompt: ["chapter_text"],
  enrich_prompt: ["word_number", "chapter_text"],
  summary_prompt: ["chapter_text", "global_summary"],
  compress_global_summary_prompt: ["global_summary"],
  update_character_state_prompt: ["chapter_text", "old_state"],
  update_plot_arcs_prompt: ["chapter_number", "chapter_text", "global_summary", "character_state", "old_plot_arcs"],
  graph_extraction_prompt: ["chapter_text"],
  single_chapter_summary_prompt: ["chapter_text"],
  reader_agent_prompt: ["global_summary", "chapter_info", "character_state", "plot_arcs"],
  villain_agent_prompt: ["chapter_info", "reader_critique", "character_state", "plot_arcs"],
  director_agent_prompt: ["chapter_info", "reader_critique", "villain_plan", "character_state", "plot_arcs"],
  interactive_rewrite_prompt: ["context_before", "selected_text", "context_after", "user_instruction", "platform_label", "platform_rules", "forbidden", "style_requirement", "genre", "topic"],
  knowledge_search_prompt: ["chapter_number", "chapter_title", "characters_involved", "key_items", "scene_location", "chapter_role", "chapter_purpose", "foreshadowing", "short_summary", "user_guidance", "time_constraint"],
  knowledge_filter_prompt: ["chapter_info", "retrieved_texts"],
  Character_Import_Prompt: ["content"],
};

// LCS Line-by-Line Diff 算法
function diffLines(oldStr: string, newStr: string) {
  const oldLines = oldStr.split('\n');
  const newLines = newStr.split('\n');
  const dp: number[][] = Array(oldLines.length + 1).fill(0).map(() => Array(newLines.length + 1).fill(0));
  
  for (let i = 1; i <= oldLines.length; i++) {
    for (let j = 1; j <= newLines.length; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }
  
  const result: { type: 'added' | 'removed' | 'unchanged'; value: string }[] = [];
  let i = oldLines.length;
  let j = newLines.length;
  
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      result.unshift({ type: 'unchanged', value: oldLines[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: 'added', value: newLines[j - 1] });
      j--;
    } else {
      result.unshift({ type: 'removed', value: oldLines[i - 1] });
      i--;
    }
  }
  return result;
}

export function PromptsTab() {
  const { project } = useProjectContext()
  const queryClient = useQueryClient()
  const [selectedKey, setSelectedKey] = React.useState<string | null>(null)
  const [editContent, setEditContent] = React.useState("")
  const [showDiff, setShowDiff] = React.useState(false)
  const [showSnapshots, setShowSnapshots] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  // 1. 获取提示词列表
  const { data, isLoading } = useQuery({
    queryKey: ["prompts", project.id],
    queryFn: () => api.prompts.list(project.id),
  })

  const prompts = React.useMemo(() => data?.prompts || [], [data?.prompts])
  const selectedPrompt = prompts.find(p => p.key === selectedKey)

  // 2. 获取当前选中提示词的历史快照
  const { data: snapshotData, refetch: refetchSnapshots } = useQuery({
    queryKey: ["prompts", project.id, selectedKey, "snapshots"],
    queryFn: () => api.prompts.snapshots(project.id, selectedKey!),
    enabled: !!selectedKey && showSnapshots,
  })

  const snapshots = snapshotData?.snapshots || []

  // 当选择不同提示词时更新编辑器内容
  React.useEffect(() => {
    if (selectedPrompt) {
      setEditContent(selectedPrompt.is_overridden ? (selectedPrompt.custom_content || "") : selectedPrompt.default_content)
      setShowDiff(false)
      setShowSnapshots(false)
    } else {
      setEditContent("")
    }
  }, [selectedPrompt])

  // 默认选中第一个
  React.useEffect(() => {
    if (prompts.length > 0 && !selectedKey) {
      setSelectedKey(prompts[0].key)
    }
  }, [prompts, selectedKey])

  // 3. 提取本地花括号占位符，执行前端实时安全校验
  const currentPlaceholders = React.useMemo(() => {
    const matches = editContent.match(/{([^{}]+)}/g) || []
    return Array.from(new Set(matches.map(m => m.slice(1, -1).trim()).filter(p => !/^\d+$/.test(p))))
  }, [editContent])

  const allowedPlaceholders = React.useMemo(() => selectedKey ? (PROMPT_ALLOWED_VARIABLES[selectedKey] || []) : [], [selectedKey])
  
  const invalidPlaceholders = React.useMemo(() => {
    return currentPlaceholders.filter(p => !allowedPlaceholders.includes(p))
  }, [currentPlaceholders, allowedPlaceholders])

  const missingPlaceholders = React.useMemo(() => {
    // 主要是给用户一些参考，有些并不一定是 mandatory，但主要用于辅助提醒
    // next_chapter_draft_prompt 中包含极多变量，我们列出一些极其核心的参考变量
    const coreVariables = ["novel_number", "chapter_title", "chapter_summary", "global_summary", "previous_chapter_excerpt"]
    if (selectedKey === "next_chapter_draft_prompt") {
      return coreVariables.filter(p => !currentPlaceholders.includes(p))
    }
    return []
  }, [selectedKey, currentPlaceholders])

  // 4. Mutations
  const saveMutation = useMutation({
    mutationFn: async (content: string) => {
      if (!selectedKey) return
      return api.prompts.update(project.id, selectedKey, content)
    },
    onSuccess: () => {
      toast.success("提示词已保存并成功生成历史快照备份！")
      queryClient.invalidateQueries({ queryKey: ["prompts", project.id] })
      if (showSnapshots) refetchSnapshots()
    },
    onError: (err: any) => {
      toast.error(err.message || "保存失败")
    }
  })

  const resetMutation = useMutation({
    mutationFn: async () => {
      if (!selectedKey) return
      return api.prompts.reset(project.id, selectedKey)
    },
    onSuccess: () => {
      toast.success("已恢复为系统默认提示词，原自定义内容已备份。")
      queryClient.invalidateQueries({ queryKey: ["prompts", project.id] })
      if (showSnapshots) refetchSnapshots()
    },
    onError: (err: any) => {
      toast.error(err.message || "重置失败")
    }
  })

  const restoreMutation = useMutation({
    mutationFn: async (snapshotId: string) => {
      if (!selectedKey) return
      return api.prompts.restore(project.id, selectedKey, snapshotId)
    },
    onSuccess: (res: any) => {
      toast.success("成功恢复至历史备份快照！")
      setEditContent(res.content || "")
      queryClient.invalidateQueries({ queryKey: ["prompts", project.id] })
      refetchSnapshots()
    },
    onError: (err: any) => {
      toast.error(err.message || "快照恢复失败")
    }
  })

  const importMutation = useMutation({
    mutationFn: async (customPrompts: Record<string, string>) => {
      return api.prompts.import(project.id, customPrompts)
    },
    onSuccess: (res: any) => {
      toast.success(res.message || "配置导入成功！")
      queryClient.invalidateQueries({ queryKey: ["prompts", project.id] })
    },
    onError: (err: any) => {
      toast.error(err.message || "导入失败")
    }
  })

  // 5. 导入导出逻辑
  const handleExport = async () => {
    try {
      const data = await api.prompts.export(project.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `novel_prompts_backup_${project.id}_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success("项目提示词配置文件导出成功！")
    } catch {
      toast.error("导出配置文件失败")
    }
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string
        const parsed = JSON.parse(text)
        if (!parsed.custom_prompts || typeof parsed.custom_prompts !== "object") {
          toast.error("文件格式有误：缺少 custom_prompts 根节点")
          return
        }
        if (confirm("导入将覆盖当前项目所有的自定义提示词（覆盖前系统会自动备份原有内容），确定继续吗？")) {
          importMutation.mutate(parsed.custom_prompts)
        }
      } catch {
        toast.error("解析 JSON 配置文件失败，请确保格式正确。")
      }
    }
    reader.readAsText(file)
    e.target.value = "" // 重置以支持同一文件重复选择
  }

  // 整理分组
  const groupedPrompts = React.useMemo(() => {
    const groups: Record<string, PromptEntry[]> = {}
    for (const p of prompts) {
      if (!groups[p.group]) groups[p.group] = []
      groups[p.group].push(p)
    }
    return groups
  }, [prompts])

  // 计算比对差异内容
  const originalCompareContent = React.useMemo(() => {
    if (!selectedPrompt) return ""
    return selectedPrompt.is_overridden ? (selectedPrompt.custom_content || "") : selectedPrompt.default_content
  }, [selectedPrompt])

  const diffResult = React.useMemo(() => {
    return diffLines(originalCompareContent, editContent)
  }, [originalCompareContent, editContent])

  const hasChanges = selectedPrompt && editContent !== (selectedPrompt.is_overridden ? selectedPrompt.custom_content : selectedPrompt.default_content)

  if (isLoading) {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[750px]">
      {/* 隐藏的导入上传 Input */}
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        accept=".json" 
        className="hidden" 
      />

      {/* 左侧侧边栏 - 提示词选择 & 导入导出 */}
      <Card className="col-span-1 glass-panel border-border/40 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-border/30 bg-primary/5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold flex items-center gap-2">
              <span className="text-lg">🧪</span> 提示词实验室
            </h2>
            <div className="flex items-center gap-1.5">
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                title="导出所有自定义提示词"
                onClick={handleExport}
              >
                <Download className="w-3.5 h-3.5" />
              </Button>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                title="导入配置文件覆盖"
                onClick={handleImportClick}
                disabled={importMutation.isPending}
              >
                {importMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            修改后实时覆盖，并伴有占位符安全校验和 10 次快照机制。
          </p>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-3 space-y-6">
            {Object.entries(groupedPrompts).map(([groupName, items]) => (
              <div key={groupName} className="space-y-2">
                <h3 className="text-xs font-bold text-muted-foreground/60 uppercase tracking-wider pl-2">
                  {groupName}
                </h3>
                <div className="space-y-1">
                  {items.map((p) => (
                    <button
                      key={p.key}
                      onClick={() => setSelectedKey(p.key)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all duration-200 flex items-center justify-between group ${
                        selectedKey === p.key
                          ? "bg-primary/20 text-primary font-medium"
                          : "hover:bg-primary/10 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span className="truncate">{p.label}</span>
                      {p.is_overridden && (
                        <div className="w-1.5 h-1.5 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.8)]" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </Card>

      {/* 右侧主工作区 - 编辑器 / Diff / 备份 */}
      <Card className="col-span-1 lg:col-span-3 glass-panel border-border/40 flex flex-col overflow-hidden relative">
        {selectedPrompt ? (
          <>
            {/* 工作区 Header */}
            <div className="p-5 border-b border-border/30 flex flex-wrap gap-4 justify-between items-start bg-secondary/10">
              <div className="flex-1 min-w-[250px]">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold">{selectedPrompt.label}</h2>
                  {selectedPrompt.is_overridden ? (
                    <Badge variant="default" className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                      已覆盖自定义
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-muted-foreground">系统默认</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
                  {selectedPrompt.description}
                </p>
                <div className="mt-2 text-xs font-mono text-muted-foreground/60 flex items-center gap-1">
                  <span className="select-all">KEY: {selectedPrompt.key}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowSnapshots(!showSnapshots)
                    setShowDiff(false)
                  }}
                  className={showSnapshots ? "bg-primary/10 text-primary border-primary/30" : ""}
                >
                  <History className="w-4 h-4 mr-1.5" />
                  备份快照
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowDiff(!showDiff)
                    setShowSnapshots(false)
                  }}
                  className={showDiff ? "bg-primary/10 text-primary border-primary/30" : ""}
                >
                  <GitCompare className="w-4 h-4 mr-1.5" />
                  对比差异
                </Button>

                {selectedPrompt.is_overridden && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={() => {
                      if (confirm("确定要恢复默认，丢弃当前的自定义修改吗？")) {
                        resetMutation.mutate()
                      }
                    }}
                    disabled={resetMutation.isPending || saveMutation.isPending}
                  >
                    <RefreshCcw className="w-4 h-4 mr-1.5" />
                    恢复默认
                  </Button>
                )}

                <Button 
                  size="sm" 
                  className={`relative overflow-hidden transition-all ${
                    hasChanges && invalidPlaceholders.length === 0 
                      ? "shadow-[0_0_15px_oklch(var(--p)/0.5)]" 
                      : ""
                  }`}
                  disabled={!hasChanges || invalidPlaceholders.length > 0 || saveMutation.isPending || resetMutation.isPending}
                  onClick={() => saveMutation.mutate(editContent)}
                >
                  {saveMutation.isPending ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <Save className="w-4 h-4 mr-1.5" />}
                  保存修改
                </Button>
              </div>
            </div>

            {/* 校验栏 (包含警告/提示) */}
            <div className="px-5 py-2.5 bg-background/50 border-b border-border/20 text-xs flex flex-wrap gap-x-6 gap-y-1.5">
              {invalidPlaceholders.length > 0 ? (
                <div className="text-red-400 font-medium flex items-center gap-1.5 animate-pulse">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                  非法的占位符：{invalidPlaceholders.map(p => `{${p}}`).join(", ")}（请删除，否则保存将受拦截）
                </div>
              ) : (
                <div className="text-green-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                  占位符安全校验已通过
                </div>
              )}

              {missingPlaceholders.length > 0 && (
                <div className="text-yellow-500 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  建议包含的核心变量：{missingPlaceholders.map(p => `{${p}}`).join(", ")}
                </div>
              )}
            </div>

            {/* 编辑与视图展示区 */}
            <div className="flex-1 relative flex overflow-hidden">
              {/* 编辑区 */}
              <div className={`flex-1 transition-all duration-300 ${showSnapshots ? "mr-72" : ""}`}>
                {showDiff ? (
                  /* Diff 对比视图 */
                  <div className="h-full w-full bg-background/30 p-6 overflow-auto font-mono text-sm leading-relaxed select-text">
                    <h3 className="text-xs text-muted-foreground/60 mb-3 flex items-center gap-1.5 font-sans">
                      <GitCompare className="w-3.5 h-3.5" /> 对比视图 (红色：删除，绿色：新增，白色：未修改)
                    </h3>
                    <div className="space-y-1 min-h-[500px]">
                      {diffResult.map((line, idx) => (
                        <div 
                          key={idx} 
                          className={`px-2 py-0.5 rounded flex items-start gap-3 border-l-2 ${
                            line.type === "added" 
                              ? "bg-green-500/10 text-green-400 border-green-500" 
                              : line.type === "removed" 
                              ? "bg-red-500/10 text-red-400 border-red-500 line-through" 
                              : "border-transparent text-muted-foreground"
                          }`}
                        >
                          <span className="text-xs select-none text-muted-foreground/40 w-8 text-right pt-0.5">
                            {idx + 1}
                          </span>
                          <span className="whitespace-pre-wrap break-all flex-1">
                            {line.value || " "}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  /* 正常文本编辑器 */
                  <div className="w-full h-full min-h-[500px] relative">
                    <Textarea
                      className="w-full h-full min-h-[500px] border-0 focus-visible:ring-0 resize-none font-mono text-sm leading-relaxed p-6 bg-transparent"
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      placeholder="在此输入提示词..."
                      spellCheck={false}
                    />
                    <div className="absolute bottom-4 right-4 pointer-events-none opacity-0 hover:opacity-100 transition-opacity">
                      <div className="bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg px-3 py-1.5 text-xs text-muted-foreground flex items-center gap-2">
                        <FileCode className="w-3.5 h-3.5 text-primary" />
                        允许的全部占位符：{allowedPlaceholders.map(p => `{${p}}`).join(", ")}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 历史快照抽屉面板 */}
              {showSnapshots && (
                <div className="w-72 border-l border-border/30 bg-secondary/15 absolute right-0 top-0 bottom-0 flex flex-col z-10 transition-all duration-300">
                  <div className="p-3 border-b border-border/30 bg-primary/5 flex items-center justify-between">
                    <span className="text-xs font-bold flex items-center gap-1.5 text-muted-foreground uppercase">
                      <History className="w-3.5 h-3.5" /> 历史备份记录
                    </span>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6" 
                      onClick={() => setShowSnapshots(false)}
                    >
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                  <ScrollArea className="flex-1">
                    <div className="p-3 space-y-3">
                      {snapshots.length === 0 ? (
                        <div className="text-center text-xs text-muted-foreground py-8">
                          暂无该提示词的快照记录
                        </div>
                      ) : (
                        snapshots.map((snap) => (
                          <div 
                            key={snap.id} 
                            className="p-2.5 rounded-lg border border-border/40 bg-background/50 hover:bg-background/80 transition-colors space-y-1.5"
                          >
                            <div className="text-xs font-semibold text-primary/80">
                              {snap.readable_time}
                            </div>
                            <div className="text-[11px] text-muted-foreground line-clamp-3 font-mono leading-relaxed bg-secondary/10 p-1.5 rounded border border-border/20">
                              {snap.preview}
                            </div>
                            <Button 
                              variant="outline" 
                              size="xs" 
                              className="w-full text-[10px] h-6 py-0 mt-1 hover:bg-primary/20 hover:text-primary"
                              onClick={() => {
                                if (confirm("恢复该版本将覆盖当前的编辑内容，确定继续吗？")) {
                                  restoreMutation.mutate(snap.id)
                                }
                              }}
                              disabled={restoreMutation.isPending}
                            >
                              恢复该版本
                            </Button>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <span className="text-4xl mb-4">🧪</span>
            <p>请在左侧选择一个提示词进行修改</p>
          </div>
        )}
      </Card>
    </div>
  )
}
