"use client"

import React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Save, Loader2, Wand2, ListChecks, Play, RefreshCw, Ban, Gauge } from "lucide-react"
import { useProjectContext } from "../ProjectContext"
import { toast } from "sonner"
import { GenerationContextViewer } from "./GenerationContextViewer"


export function WorkbenchControls() {
  const {
    projectId,
    updateConfig,
    generation: {
      generationTaskId, generationStopping, isConnected,
      generationChapterCount, setGenerationChapterCount,
      generationWordCount, setGenerationWordCount,
      batchChapterCount, setBatchChapterCount,
      handleStopGeneration, startTask,
      enableBrainstorming
    },
    workbench: {
      selectedChapterNumber, setSelectedChapterNumber,
    },
    platform: {
      setHookChapterNum
    }
  } = useProjectContext()

  const handleApplyGenerationTargets = () => {
    updateConfig.mutate({
      num_chapters: generationChapterCount,
      word_number: generationWordCount,
    }, { onSuccess: () => toast.success("保存生成控制成功") })
  }

  const handleGenerateArchitecture = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      startTask("architecture", `/api/v1/projects/${projectId}/generate/architecture`, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateBlueprint = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      startTask("blueprint", `/api/v1/projects/${projectId}/generate/blueprint`, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateWorkbenchChapter = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      const url = `/api/v1/projects/${projectId}/generate/chapter/${selectedChapterNumber}${enableBrainstorming ? "?enable_brainstorming=true" : ""}`
      startTask("chapter", url, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const handleGenerateChapterBatch = async () => {
    try {
      const taskId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15)
      const url = `/api/v1/projects/${projectId}/generate/chapters?start_chapter=${selectedChapterNumber}&count=${batchChapterCount}${enableBrainstorming ? "&enable_brainstorming=true" : ""}`
      startTask("chapterBatch", url, taskId)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  return (
    <Card className="glass-panel border-border/40 hover:shadow-[0_0_30px_oklch(0.68_0.19_285/0.1)] transition-all duration-500">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-base font-bold text-gradient-primary w-fit">
          <Gauge className="h-5 w-5 text-primary" />生成控制
        </CardTitle>
        <CardDescription>控制架构、目录和章节草稿的生成规模</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[150px_150px_150px_150px_minmax(0,1fr)]">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">总章节</Label>
            <Input
              type="number"
              min={1}
              value={generationChapterCount}
              onChange={(event) => setGenerationChapterCount(Math.max(1, Number(event.target.value) || 1))}
              className="bg-background/50"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">每章字数</Label>
            <Input
              type="number"
              min={500}
              step={500}
              value={generationWordCount}
              onChange={(event) => setGenerationWordCount(Math.max(500, Number(event.target.value) || 500))}
              className="bg-background/50"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">当前章节</Label>
            <Input
              type="number"
              min={1}
              max={generationChapterCount || undefined}
              value={selectedChapterNumber}
              onChange={(event) => {
                const value = Math.max(1, Number(event.target.value) || 1)
                setSelectedChapterNumber(value)
                setHookChapterNum(value)
              }}
              className="bg-background/50"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">本轮章数</Label>
            <Input
              type="number"
              min={1}
              max={20}
              value={batchChapterCount}
              onChange={(event) => setBatchChapterCount(Math.min(20, Math.max(1, Number(event.target.value) || 1)))}
              className="bg-background/50"
            />
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <Button 
              variant="outline" 
              onClick={handleApplyGenerationTargets} 
              disabled={updateConfig.isPending}
              className="bg-card/40 border-border/80"
            >
              {updateConfig.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2 text-indigo-400" />}
              保存控制
            </Button>
            <Button 
              onClick={handleGenerateArchitecture} 
              disabled={isConnected || Boolean(generationTaskId) || generationStopping}
              className="shadow-md shadow-primary/10"
            >
              <Wand2 className="h-4 w-4 mr-2" />生成架构
            </Button>
            <Button 
              onClick={handleGenerateBlueprint} 
              disabled={isConnected || Boolean(generationTaskId) || generationStopping} 
              variant="outline"
              className="bg-card/40 border-border/80"
            >
              <ListChecks className="h-4 w-4 mr-2 text-purple-400" />生成目录
            </Button>
            <Button 
              onClick={handleGenerateWorkbenchChapter} 
              disabled={isConnected || Boolean(generationTaskId) || generationStopping} 
              variant="outline"
              className="bg-card/40 border-border/80"
            >
              <Play className="h-4 w-4 mr-2 text-emerald-400" />生成本章
            </Button>
            <Button 
              onClick={handleGenerateChapterBatch} 
              disabled={isConnected || Boolean(generationTaskId) || generationStopping} 
              variant="outline"
              className="bg-card/40 border-border/80"
            >
              <RefreshCw className="h-4 w-4 mr-2 text-blue-400" />批量生成
            </Button>
            {generationTaskId && (
              <Button variant="destructive" onClick={handleStopGeneration} disabled={generationStopping}>
                {generationStopping ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Ban className="h-4 w-4 mr-2" />}
                中断生成
              </Button>
            )}
            <GenerationContextViewer />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
