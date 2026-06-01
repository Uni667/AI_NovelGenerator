import { Project } from "../types"

export interface StorageUsage {
  bytes: number
  formatted: string
  percentage: number
}

export interface ProjectStats {
  total: number
  ready: number
  draft: number
  lastUpdated: string
}

export const projectService = {
  // Stats Calculator
  calculateStats: (projects: Project[]): ProjectStats => {
    if (!projects || projects.length === 0) {
      return { total: 0, ready: 0, draft: 0, lastUpdated: "无近期更新" }
    }
    const total = projects.length
    const ready = projects.filter(p => p.status === "ready").length
    const draft = projects.filter(p => p.status === "draft").length
    
    // Find the latest update time
    let latestTime = 0
    projects.forEach(p => {
      const t = new Date(p.updated_at).getTime()
      if (t > latestTime) latestTime = t
    })
    
    const lastUpdated = latestTime > 0 
      ? new Date(latestTime).toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" })
      : "无近期更新"
      
    return { total, ready, draft, lastUpdated }
  },

  // Storage Estimator
  estimateStorageUsage: (projects: Project[]): StorageUsage => {
    if (!projects || projects.length === 0) {
      return { bytes: 0, formatted: "0.0 MB", percentage: 0 }
    }
    let totalBytes = 0
    projects.forEach(p => {
      // Base size: 1.2MB per project
      let projectBytes = 1.2 * 1024 * 1024
      // Increase size deterministically based on metadata length
      projectBytes += (p.name.length + (p.description?.length || 0)) * 50 * 1024
      
      // Status adds size
      if (p.status === "ready") {
        projectBytes += 1.8 * 1024 * 1024
      } else if (p.status === "generating") {
        projectBytes += 0.9 * 1024 * 1024
      }
      
      totalBytes += projectBytes
    })

    // 10 GB limit for Pro version
    const limitBytes = 10 * 1024 * 1024 * 1024
    const percentage = Math.min(100, Math.max(1, Math.round((totalBytes / limitBytes) * 100)))
    
    const mb = totalBytes / (1024 * 1024)
    let formatted = ""
    if (mb >= 1024) {
      formatted = `${(mb / 1024).toFixed(2)} GB`
    } else {
      formatted = `${mb.toFixed(1)} MB`
    }
    
    return { bytes: totalBytes, formatted, percentage }
  }
}
