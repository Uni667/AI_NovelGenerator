"use client"

import React from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { HelpCircle } from "lucide-react"

export function HelpGuideModal() {
  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" size="sm" className="gap-1" />}>
        <HelpCircle className="h-4 w-4" />
        使用指南
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>小说生成器写作指南</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm leading-relaxed mt-4">
          <p>欢迎使用 AI 小说生成器！为了保证生成的连贯性，请遵循以下推荐工作流：</p>
          
          <div className="bg-muted p-4 rounded-md space-y-2">
            <h4 className="font-medium text-base">1. 前期准备</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>先在“项目配置”中生成<strong>小说架构</strong>，建立世界观和人物骨架。</li>
              <li>接着生成<strong>章节目录</strong>，规划初期的剧情走向。</li>
            </ul>
          </div>
          
          <div className="bg-muted p-4 rounded-md space-y-2">
            <h4 className="font-medium text-base">2. 章节创作 (Workbench)</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>在“工作台”中生成单个章节的正文草稿。</li>
              <li>如果您对生成的章节满意，请点击<strong>定稿</strong>。</li>
              <li>定稿后，系统会从该章提取状态变化（如人物出场、死亡、揭名等），生成一个 <code>State Patch</code> (状态补丁)。</li>
            </ul>
          </div>
          
          <div className="bg-muted p-4 rounded-md space-y-2">
            <h4 className="font-medium text-base">3. 状态确认 (State Tab)</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>定稿后请务必到 <strong>状态页 (State)</strong> 查看待处理的 Patch。</li>
              <li>如果您认为提取的内容正确，请<strong>合并</strong>它。合并后的状态将永久影响后续章节。</li>
              <li>如果 AI 提取有误（比如错误地记录了主角死亡），您可以直接废弃或进入对应状态页手动修正。</li>
            </ul>
          </div>
          
          <div className="bg-muted p-4 rounded-md space-y-2">
            <h4 className="font-medium text-base">4. 长期维护</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong>大纲演化</strong>：当剧情偏离原定大纲时，可以在大纲页生成演化建议，只会调整未来的未写章节。</li>
              <li><strong>备份与导出</strong>：系统会在您修改高危设定前自动备份。您也可以随时“导出设定包”留存。</li>
            </ul>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
