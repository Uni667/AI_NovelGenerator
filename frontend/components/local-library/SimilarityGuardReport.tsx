"use client"

import { useEffect, useState } from "react"
import { ShieldAlert, ShieldCheck, FileText, AlertTriangle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { api } from "@/lib/api-client"

export function SimilarityGuardReport({ projectId, chapterNumber }: { projectId?: string; chapterNumber?: number }) {
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (projectId && chapterNumber) {
      setLoading(true)
      api.chapters.getSimilarityReport(projectId, chapterNumber)
        .then(setReport)
        .catch(() => setReport(null))
        .finally(() => setLoading(false))
    }
  }, [projectId, chapterNumber])

  if (!projectId || !chapterNumber) {
    return (
      <Card className="glass-panel border-border/40">
        <CardHeader className="pb-3 border-b border-border/30">
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-primary" /> 融梗/照抄检测
          </CardTitle>
          <CardDescription className="text-xs">
            在生成创作内容后，自动对比已绑定的本地库，防止文本过度相似。
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 flex items-center justify-center h-[120px]">
          <div className="text-sm text-muted-foreground bg-muted/20 px-4 py-2 rounded-lg border border-dashed border-border/50 text-center space-y-1">
            <p>防照抄守卫已内置于 <strong>章节生成管线</strong> 中</p>
            <p className="text-xs">只要在项目参考库中开启「防照抄检测」，生成时就会自动校验重写。</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground animate-pulse">正在获取查重报告...</div>
  }

  if (!report) {
    return (
      <div className="text-sm text-muted-foreground">
        暂无查重报告（可能未开启检测或报告不存在）
      </div>
    )
  }

  return (
    <Card className="glass-panel border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <CardTitle className="text-base flex items-center gap-2">
          {report.needs_rewrite ? (
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          ) : (
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          )}
          查重报告 (第 {chapterNumber} 章)
        </CardTitle>
        <CardDescription className="text-xs">
          检测时间: {new Date(report.timestamp).toLocaleString()}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 space-y-3 text-sm">
        <div className="flex justify-between items-center border-b border-border/20 pb-2">
          <span className="text-muted-foreground">n-gram 重合率</span>
          <span className="font-mono">{(report.max_ngram_overlap_ratio * 100).toFixed(2)}%</span>
        </div>
        <div className="flex justify-between items-center border-b border-border/20 pb-2">
          <span className="text-muted-foreground">长句重复匹配数</span>
          <span className="font-mono">{report.long_sentence_match_count}</span>
        </div>
        <div className="flex justify-between items-center border-b border-border/20 pb-2">
          <span className="text-muted-foreground">专有名词重合数</span>
          <span className="font-mono">{report.proper_noun_overlap_count}</span>
        </div>
        
        {report.reasons && report.reasons.length > 0 && (
          <div className="mt-4 pt-2">
            <p className="text-xs text-amber-500 font-medium mb-2">拦截原因：</p>
            <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1">
              {report.reasons.map((r: string, i: number) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
