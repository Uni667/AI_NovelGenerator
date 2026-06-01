"use client"

import React, { useState } from "react"

interface CharacterAvatarProps {
  character: {
    name: string
    avatarUrl?: string
    generatedAvatarUrl?: string
    chibiAvatarUrl?: string
    roleType?: string
  } | null
  size?: "sm" | "md" | "lg" | "xl"
  className?: string
}

export function CharacterAvatar({ character, size = "md", className = "" }: CharacterAvatarProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const name = character?.name || "未知"
  const initials = name.slice(0, 2)
  
  const sizeClasses = {
    sm: "w-8 h-8 text-xs",
    md: "w-12 h-12 text-sm",
    lg: "w-16 h-16 text-lg",
    xl: "w-20 h-20 text-xl",
  }

  // Get gradient background depending on roleType
  const getRoleBg = (role?: string) => {
    switch (role) {
      case "主角":
        return "bg-gradient-to-br from-violet-600 to-indigo-700 text-white border-violet-500/30"
      case "女主":
        return "bg-gradient-to-br from-pink-500 to-purple-600 text-white border-pink-500/30"
      case "反派":
        return "bg-gradient-to-br from-rose-600 to-red-800 text-white border-rose-500/30"
      case "配角":
        return "bg-gradient-to-br from-blue-500 to-cyan-600 text-white border-blue-500/30"
      default:
        return "bg-gradient-to-br from-slate-600 to-zinc-700 text-white border-slate-500/30"
    }
  }

  const avatarUrl = character?.avatarUrl || character?.generatedAvatarUrl || character?.chibiAvatarUrl

  if (avatarUrl && !imgFailed) {
    return (
      <img
        src={avatarUrl}
        alt={name}
        onError={() => setImgFailed(true)}
        className={`rounded-full object-cover border border-white/10 ${sizeClasses[size]} ${className}`}
      />
    )
  }

  return (
    <div className={`rounded-full flex items-center justify-center font-bold tracking-wider border select-none shadow-md ${getRoleBg(character?.roleType)} ${sizeClasses[size]} ${className}`}>
      {initials}
    </div>
  )
}
