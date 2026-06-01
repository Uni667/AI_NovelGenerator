// src/components/project/CharacterCard.tsx
"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { LucideProps } from "lucide-react"
import { CharacterAvatar } from "./CharacterAvatar"
import { VisualizerCharacter } from "@/lib/types"
import { Sparkles, Loader2, Copy, Check } from "lucide-react"

interface CharacterCardProps {
  character: VisualizerCharacter
  onClick?: (id: string) => void
  onGeneratePrompt?: (charId: string) => void
  onGenerateAvatar?: (charId: string) => void
  generatingId?: string | null // e.g., `character_${id}` or `image_${id}`
  copiedId?: string | null
  onCopy?: (text: string, id: string) => void
}

export const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  onClick,
  onGeneratePrompt,
  onGenerateAvatar,
  generatingId,
  copiedId,
  onCopy,
}) => {
  const gradient = character.roleType === "主角"
    ? "from-violet-600/20 to-indigo-900/10"
    : character.roleType === "女主"
    ? "from-pink-600/20 to-purple-900/10"
    : character.roleType === "反派"
    ? "from-rose-800/20 to-red-950/10"
    : "from-slate-700/20 to-slate-900/10"

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onCopy && character.avatarPrompt) {
      onCopy(character.avatarPrompt, `avatar_${character.id}`)
    }
  }

  return (
    <Card className={`glass-card border-border/40 overflow-hidden flex flex-col hover:border-primary/30 transition-all duration-300 group ${onClick ? "cursor-pointer" : ""}`}> 
      {/* Avatar */}
      <div className={`relative w-full aspect-[4/5] bg-gradient-to-br ${gradient} flex flex-col items-center justify-center p-4 overflow-hidden border-b border-white/5`}>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]" />
        <CharacterAvatar character={character} size="lg" className="filter drop-shadow-[0_8px_16px_rgba(0,0,0,0.5)] transform group-hover:scale-110 transition-transform duration-300" />
        <div className="absolute bottom-2 left-2 right-2">
          {character.avatarPrompt ? (
            <div className="bg-slate-950/90 backdrop-blur-md p-2 rounded-lg border border-white/5 space-y-1">
              <span className="text-[9px] font-bold text-indigo-400 block uppercase tracking-wide">🎨 AI 头像提示词 (Prompt)</span>
              <p className="text-[10px] text-slate-300 line-clamp-2 leading-tight font-mono">{character.avatarPrompt}</p>
              {character.avatarUrl && (
                <div className="flex justify-between items-center pt-1 border-t border-white/5">
                  <Button size="xs" className="h-5 px-2 text-[9px] bg-primary hover:bg-primary/80 font-bold" onClick={(e) => { e.stopPropagation(); onGenerateAvatar?.(character.id) }} disabled={generatingId === `image_${character.id}`}>
                    {generatingId === `image_${character.id}` ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sparkles className="h-3 w-3 mr-1" />}生成形象
                  </Button>
                  <Button size="xs" variant="ghost" className="h-5 px-1.5 text-[9px] hover:bg-white/10" onClick={handleCopy}>
                    {copiedId === `avatar_${character.id}` ? <Check className="h-3 w-3 mr-1 text-emerald-400" /> : <Copy className="h-3 w-3 mr-1" />}复制
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <Button size="xs" className="w-full bg-slate-950/80 hover:bg-slate-900 border border-white/5 text-[9px] h-7" onClick={(e) => { e.stopPropagation(); onGeneratePrompt?.(character.id) }} disabled={generatingId === `character_${character.id}`}>
              {generatingId === `character_${character.id}` ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sparkles className="h-3 w-3 mr-1 text-primary" />}提取并生成形象提示词
            </Button>
          )}
        </div>
      </div>
      {/* Card Content */}
      <CardContent className="p-3 flex-1 flex flex-col justify-between gap-2.5">
        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-bold text-sm text-slate-100 flex items-center gap-1.5">
              {character.name}
              {character.isUnconfirmed && (
                <Badge variant="outline" className="border-amber-500/30 text-amber-500 bg-amber-500/5 text-[8px] h-4">待确认</Badge>
              )}
            </span>
            <Badge variant="outline" className={`text-[10px] ${getRoleBadgeStyle(character.roleType)}`}>{character.roleType}</Badge>
          </div>
          <div className="flex flex-wrap gap-1 text-[10px] text-muted-foreground">
            <span>{character.gender || "不明"}</span>
            <span>•</span>
            <span>{character.age || "不明"}</span>
            <span>•</span>
            <span className="text-violet-400">{character.faction || "未知"}</span>
          </div>
          <p className="text-[11px] text-[#A3A3C2] line-clamp-2 leading-relaxed bg-black/10 p-2 rounded-lg border border-white/5">
            {character.identity || "普通角色"}：{character.appearance || "暂无细节样貌描述。"}
          </p>
        </div>
        <div className="flex items-center justify-between gap-2 border-t border-border/20 pt-2 text-[10px] text-muted-foreground font-medium">
          <span>出场: 第 {character.firstChapterId ?? "?"} 章</span>
          <Button variant="link" size="xs" onClick={() => onClick?.(character.id)} className="h-5 px-1.5 text-violet-400 hover:text-violet-300 font-bold">
            查看详情
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// Helper for role badge styling (mirrors logic in VisualizerTab)
function getRoleBadgeStyle(role?: string) {
  switch (role) {
    case "主角": return "bg-violet-500/10 text-violet-400 border-violet-500/20"
    case "女主": return "bg-pink-500/10 text-pink-400 border-pink-500/20"
    case "反派": return "bg-rose-500/10 text-rose-400 border-rose-500/20"
    case "配角": return "bg-blue-500/10 text-blue-400 border-blue-500/20"
    case "NPC": return "bg-slate-500/10 text-slate-400 border-slate-500/20"
    default: return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
  }
}
