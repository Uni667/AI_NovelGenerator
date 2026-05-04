import { getToken } from "./auth"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

function authHeaders(): Record<string, string> {
  const token = getToken()
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

function formatErrorDetail(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail
      .map((item: any) => {
        const loc = Array.isArray(item?.loc) ? item.loc.join(".") : ""
        const msg = item?.msg || JSON.stringify(item)
        return loc ? `${loc}: ${msg}` : msg
      })
      .join("; ")
  }
  if (detail && typeof detail === "object") {
    const value = detail as { message?: string; error?: string }
    return value.message || value.error || JSON.stringify(detail)
  }
  return typeof detail === "string" ? detail : ""
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const method = options?.method || "GET"
  const res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
  })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = formatErrorDetail(body.detail) || body.message || message
    } catch {
      const text = await res.text()
      if (text) message = text
    }
    if (res.status === 401 && typeof window !== "undefined") {
      const { clearToken } = await import("./auth")
      clearToken()
      // 不在此处硬刷新，由 AuthGuard 统一处理路由跳转，避免刷新循环
    }
    throw new Error(`接口请求失败（${method} ${url}，${res.status}）: ${message}`)
  }
  const contentType = res.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    return res.json()
  }
  return (await res.text()) as unknown as T
}

function sseUrl(path: string, taskId?: string): string {
  const url = new URL(`${BASE_URL}${path}`)
  const token = getToken()
  if (taskId) {
    url.searchParams.set("task_id", taskId)
  }
  if (token) {
    url.searchParams.set("token", token)
  }
  return url.toString()
}

export const api = {
  projects: {
    list: () => request<any[]>("/api/v1/projects"),
    get: (id: string) => request<any>(`/api/v1/projects/${id}`),
    create: (data: any) => request<any>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: any) => request<any>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
    config: (id: string) => request<any>(`/api/v1/projects/${id}/config`),
    updateConfig: (id: string, data: any) => request<any>(`/api/v1/projects/${id}/config`, { method: "PUT", body: JSON.stringify(data) }),
  },
  chapters: {
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/chapters`),
    get: (projectId: string, num: number) => request<any>(`/api/v1/projects/${projectId}/chapters/${num}`),
    update: (projectId: string, num: number, data: any) => request<any>(`/api/v1/projects/${projectId}/chapters/${num}`, { method: "PUT", body: JSON.stringify(data) }),
  },
  files: {
    get: (projectId: string, filename: string) => request<string>(`/api/v1/projects/${projectId}/files/${encodeURIComponent(filename)}`),
    delete: (projectId: string, filename: string) => request<{ message: string; filename: string }>(`/api/v1/projects/${projectId}/files/${encodeURIComponent(filename)}`, { method: "DELETE" }),
  },
  config: {
    // API 凭证
    listCredentials: () => request<any[]>("/api/user/api-credentials"),
    createCredential: (data: { name: string; provider: string; api_key: string; base_url: string; is_default?: boolean }) =>
      request<any>("/api/user/api-credentials", { method: "POST", body: JSON.stringify(data) }),
    updateCredential: (id: string, data: any) =>
      request<any>(`/api/user/api-credentials/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteCredential: (id: string) =>
      request<any>(`/api/user/api-credentials/${id}`, { method: "DELETE" }),
    testCredential: (id: string) =>
      request<{ success: boolean; message: string }>(`/api/user/api-credentials/${id}/test`, { method: "POST" }),
    enableCredential: (id: string) =>
      request<any>(`/api/user/api-credentials/${id}/enable`, { method: "POST" }),
    disableCredential: (id: string) =>
      request<any>(`/api/user/api-credentials/${id}/disable`, { method: "POST" }),
    // 模型配置
    listProfiles: () => request<any[]>("/api/user/model-profiles"),
    getProfile: (id: string) => request<any>(`/api/user/model-profiles/${id}`),
    createProfile: (data: any) =>
      request<any>("/api/user/model-profiles", { method: "POST", body: JSON.stringify(data) }),
    updateProfile: (id: string, data: any) =>
      request<any>(`/api/user/model-profiles/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteProfile: (id: string) =>
      request<any>(`/api/user/model-profiles/${id}`, { method: "DELETE" }),
    testProfile: (id: string) =>
      request<{ success: boolean; message: string }>(`/api/user/model-profiles/${id}/test`, { method: "POST" }),
    setDefaultProfile: (id: string) =>
      request<any>(`/api/user/model-profiles/${id}/set-default`, { method: "POST" }),
    // 调用日志
    listInvocationLogs: (limit?: number) =>
      request<any[]>(`/api/user/model-invocation-logs?limit=${limit || 50}`),
    listProjectInvocationLogs: (projectId: string, limit?: number) =>
      request<any[]>(`/api/projects/${projectId}/model-invocation-logs?limit=${limit || 30}`),
  },
  modelAssignment: {
    get: (projectId: string) => request<any>(`/api/projects/${projectId}/model-assignment`),
    save: (projectId: string, data: any) =>
      request<any>(`/api/projects/${projectId}/model-assignment`, { method: "PUT", body: JSON.stringify(data) }),
  },
  knowledge: {
    upload: (projectId: string, file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      return fetch(`${BASE_URL}/api/v1/projects/${projectId}/knowledge/upload`, {
        method: "POST",
        body: formData,
        headers: authHeaders(),
      }).then(async (res) => {
        if (!res.ok) {
          let message = res.statusText
          try {
            const body = await res.json()
            message = formatErrorDetail(body.detail) || body.message || message
          } catch {
            const text = await res.text()
            if (text) message = text
          }
          throw new Error(`知识库上传失败: ${message}`)
        }
        return res.json()
      })
    },
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/knowledge/files`),
    delete: (projectId: string, fileId: number) => request<any>(`/api/v1/projects/${projectId}/knowledge/files/${fileId}`, { method: "DELETE" }),
    reimport: (projectId: string, fileId: number) => request<any>(`/api/v1/projects/${projectId}/knowledge/files/${fileId}/reimport`, { method: "POST" }),
    clearVector: (projectId: string) => request<void>(`/api/v1/projects/${projectId}/knowledge/clear-vector`, { method: "DELETE" }),
  },
  generate: {
    architecture: (projectId: string, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/architecture`, taskId)),
    blueprint: (projectId: string, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/blueprint`, taskId)),
    chapter: (projectId: string, num: number, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/chapter/${num}`, taskId)),
    chapterBatch: (projectId: string, startChapter: number, count: number, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/chapters?start_chapter=${startChapter}&count=${count}`, taskId)),
    finalize: (projectId: string, num: number, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/finalize/${num}`, taskId)),
    taskStatus: (projectId: string, taskId: string) => request<any>(`/api/v1/projects/${projectId}/generate/tasks/${taskId}`),
    cancelTask: (projectId: string, taskId: string) => request<any>(`/api/v1/projects/${projectId}/generate/tasks/${taskId}/cancel`, { method: "POST" }),
    retryTask: (projectId: string, taskId: string) => request<any>(`/api/v1/projects/${projectId}/generate/tasks/${taskId}/retry`, { method: "POST" }),
    listTasks: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/generate/tasks`),
  },
  characters: {
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/characters`),
    create: (projectId: string, data: { name: string; description?: string; status?: string; source?: string; first_appearance_chapter?: number | null }) => request<any>(`/api/v1/projects/${projectId}/characters`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, charId: number, data: any) => request<any>(`/api/v1/projects/${projectId}/characters/${charId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, charId: number) => request<void>(`/api/v1/projects/${projectId}/characters/${charId}`, { method: "DELETE" }),
    importPreview: (projectId: string) => request<{ summary: any; candidates: any[] }>(`/api/v1/projects/${projectId}/characters/import-from-state/preview`, { method: "POST" }),
    importFromState: (projectId: string, data?: { selected_candidate_ids: string[] }) => request<any>(`/api/v1/projects/${projectId}/characters/import-from-state`, { method: "POST", body: JSON.stringify(data || {}) }),
    suggest: (projectId: string) => request<{ characters: any[] }>(`/api/v1/projects/${projectId}/characters/suggest`, { method: "POST" }),
    dashboard: (projectId: string) => request<any>(`/api/v1/projects/${projectId}/characters/dashboard`),
  },
  characterRelationships: {
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/character-relationships`),
    create: (projectId: string, data: any) => request<any>(`/api/v1/projects/${projectId}/character-relationships`, { method: "POST", body: JSON.stringify(data) }),
    createBatch: (projectId: string, data: any[]) => request<{ created: number; ids: number[] }>(`/api/v1/projects/${projectId}/character-relationships/batch`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, relId: number, data: any) => request<any>(`/api/v1/projects/${projectId}/character-relationships/${relId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, relId: number) => request<void>(`/api/v1/projects/${projectId}/character-relationships/${relId}`, { method: "DELETE" }),
    graph: (projectId: string) => request<any>(`/api/v1/projects/${projectId}/character-relationships/graph`),
    types: () => request<{ types: any[]; statuses: string[] }>(`/api/v1/character-relationship-types`),
  },
  characterConflicts: {
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/character-conflicts`),
    create: (projectId: string, data: any) => request<any>(`/api/v1/projects/${projectId}/character-conflicts`, { method: "POST", body: JSON.stringify(data) }),
    createBatch: (projectId: string, data: any[]) => request<{ created: number; ids: number[] }>(`/api/v1/projects/${projectId}/character-conflicts/batch`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, conflictId: number, data: any) => request<any>(`/api/v1/projects/${projectId}/character-conflicts/${conflictId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, conflictId: number) => request<void>(`/api/v1/projects/${projectId}/character-conflicts/${conflictId}`, { method: "DELETE" }),
    types: () => request<any>(`/api/v1/character-conflict-types`),
  },
  characterAppearances: {
    list: (projectId: string, params?: { character_id?: number; chapter_number?: number }) => {
      let url = `/api/v1/projects/${projectId}/character-appearances`
      if (params?.character_id) url += `?character_id=${params.character_id}`
      else if (params?.chapter_number) url += `?chapter_number=${params.chapter_number}`
      return request<any[]>(url)
    },
    create: (projectId: string, data: any) => request<any>(`/api/v1/projects/${projectId}/character-appearances`, { method: "POST", body: JSON.stringify(data) }),
    createBatch: (projectId: string, data: any[]) => request<{ created: number; ids: number[] }>(`/api/v1/projects/${projectId}/character-appearances/batch`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, appearanceId: number, data: any) => request<any>(`/api/v1/projects/${projectId}/character-appearances/${appearanceId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, appearanceId: number) => request<void>(`/api/v1/projects/${projectId}/character-appearances/${appearanceId}`, { method: "DELETE" }),
    timeline: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/character-appearances/timeline`),
    types: () => request<any>(`/api/v1/character-appearance-types`),
  },
  export: {
    download: (projectId: string, format: "txt" | "html" = "txt") => {
      window.open(sseUrl(`/api/v1/projects/${projectId}/export?format=${format}`), "_blank")
    },
  },
  projectFiles: {
    import: (projectId: string, file: File, fileType: string, setCurrent: boolean) => {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("file_type", fileType)
      formData.append("set_current", String(setCurrent))
      return fetch(`${BASE_URL}/api/v1/projects/${projectId}/files/import`, {
        method: "POST",
        body: formData,
        headers: authHeaders(),
      }).then(async (res) => {
        if (!res.ok) {
          let message = res.statusText
          try {
            const body = await res.json()
            message = formatErrorDetail(body.detail) || body.message || message
          } catch {
            const text = await res.text()
            if (text) message = text
          }
          throw new Error(`导入失败: ${message}`)
        }
        return res.json()
      })
    },
    list: (projectId: string, fileType?: string) => {
      const qs = fileType ? `?type=${encodeURIComponent(fileType)}` : ""
      return request<any[]>(`/api/v1/projects/${projectId}/project-files${qs}`)
    },
    setCurrent: (projectId: string, fileId: string) =>
      request<any>(`/api/v1/projects/${projectId}/project-files/${fileId}/set-current`, { method: "PUT" }),
    getCurrentArchitecture: (projectId: string) =>
      request<any>(`/api/v1/projects/${projectId}/current-architecture`).catch(() => null),
    getCurrentOutline: (projectId: string) =>
      request<any>(`/api/v1/projects/${projectId}/current-outline`).catch(() => null),
    delete: (projectId: string, fileId: string) =>
      request<{ message: string }>(`/api/v1/projects/${projectId}/project-files/${fileId}`, { method: "DELETE" }),
  },
  platform: {
    titles: (projectId: string) => request<{ titles: string[] }>(`/api/v1/projects/${projectId}/tools/titles`, { method: "POST" }),
    blurb: (projectId: string) => request<{ blurbs: string[] }>(`/api/v1/projects/${projectId}/tools/blurb`, { method: "POST" }),
    hookCheck: (projectId: string, chapterNumber = 1) => request<{ analysis: any }>(`/api/v1/projects/${projectId}/tools/hook-check?chapter_number=${chapterNumber}`, { method: "POST" }),
    chapterHookCheck: (projectId: string, chapterNumber: number) => request<{ analysis: any }>(`/api/v1/projects/${projectId}/tools/chapter-hook-check?chapter_number=${chapterNumber}`, { method: "POST" }),
    batchHookCheck: (projectId: string) => request<{ chapters: any[] }>(`/api/v1/projects/${projectId}/tools/batch-hook-check`, { method: "POST" }),
    tags: (projectId: string) => request<{ tags: any }>(`/api/v1/projects/${projectId}/tools/tags`, { method: "POST" }),
    chapterTitle: (projectId: string, chapterNumber: number) => request<{ titles: string[] }>(`/api/v1/projects/${projectId}/tools/chapter-title?chapter_number=${chapterNumber}`, { method: "POST" }),
  },
}
