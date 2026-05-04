"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { FileCheck, FileText, FileUp, FileWarning, ListChecks, RefreshCw } from "lucide-react"

import { ProjectFile, FILE_SOURCE_LABELS } from "@/lib/types"

interface Props {
  outline: ProjectFile | null
  hasArchitecture: boolean
  isLoading: boolean
  onImport: () => void
  onRegenerate: () => void
  onPreview: () => void
}

export function OutlineStatusCard({
  outline,
  hasArchitecture,
  isLoading,
  onImport,
  onRegenerate,
  onPreview,
}: Props) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-4 w-full mb-2" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    )
  }

  if (!hasArchitecture) {
    return (
      <Card className="border-muted bg-muted/20">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base text-muted-foreground">
            <ListChecks className="h-5 w-5" />
            章节目录
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            请先生成或导入小说架构，再生成章节目录。
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!outline) {
    return (
      <Card className="border-destructive/40 bg-destructive/5">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileWarning className="h-5 w-5 text-destructive" />
            章节目录
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-3">
            尚未生成或导入章节目录。生成章节内容需要目录作为写作路径。
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={onRegenerate}>
              <RefreshCw className="h-4 w-4 mr-1" /> AI 生成
            </Button>
            <Button variant="outline" size="sm" onClick={onImport}>
              <FileUp className="h-4 w-4 mr-1" /> 导入文件
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-green-500/40">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <FileCheck className="h-5 w-5 text-green-500" />
          章节目录
          <Badge
            variant={
              outline.source === "ai_generated" ? "default" : "secondary"
            }
          >
            {FILE_SOURCE_LABELS[outline.source] || outline.source}
          </Badge>
          {outline.is_current && (
            <Badge variant="outline" className="text-green-600 border-green-600">
              当前使用
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground mb-1">
          更新时间: {new Date(outline.updated_at).toLocaleString("zh-CN")}
        </p>
        <div className="flex gap-2 mt-2">
          <Button variant="outline" size="sm" onClick={onRegenerate}>
            <RefreshCw className="h-4 w-4 mr-1" /> 重新生成
          </Button>
          <Button variant="outline" size="sm" onClick={onImport}>
            <FileUp className="h-4 w-4 mr-1" /> 导入新目录
          </Button>
          <Button variant="ghost" size="sm" onClick={onPreview}>
            <FileText className="h-4 w-4 mr-1" /> 预览
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
