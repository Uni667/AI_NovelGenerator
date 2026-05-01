import { getToken } from "./auth"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

function authHeaders(): Record<string, string> {
  const token = getToken()
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = body.detail || body.message || message
    } catch {
      const text = await res.text()
      if (text) message = text
    }
    if (res.status === 401 && typeof window !== "undefined") {
      const { clearToken } = await import("./auth")
      clearToken()
      window.location.href = "/login"
    }
    throw new Error(message)
  }
  const contentType = res.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    return res.json()
  }
  return undefined as unknown as T
}

function sseUrl(path: string): string {
  const token = getToken()
  const sep = path.includes("?") ? "&" : "?"
  return `${BASE_URL}${path}${sep}token=${encodeURIComponent(token || "")}`
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
    get: (projectId: string, filename: string) => fetch(`${BASE_URL}/api/v1/projects/${projectId}/files/${filename}`, { headers: authHeaders() }).then(r => r.text()),
  },
  config: {
    llmList: () => request<Record<string, any>>("/api/v1/config/llm"),
    llmCreate: (data: any) => request<any>("/api/v1/config/llm", { method: "POST", body: JSON.stringify(data) }),
    llmUpdate: (name: string, data: any) => request<any>(`/api/v1/config/llm/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(data) }),
    llmDelete: (name: string) => request<void>(`/api/v1/config/llm/${encodeURIComponent(name)}`, { method: "DELETE" }),
    llmTest: (name: string) => request<any>(`/api/v1/config/llm/${encodeURIComponent(name)}/test`, { method: "POST" }),
    embList: () => request<Record<string, any>>("/api/v1/config/embedding"),
    embCreate: (data: any) => request<any>("/api/v1/config/embedding", { method: "POST", body: JSON.stringify(data) }),
    embDelete: (name: string) => request<void>(`/api/v1/config/embedding/${encodeURIComponent(name)}`, { method: "DELETE" }),
    embTest: (name: string) => request<any>(`/api/v1/config/embedding/${encodeURIComponent(name)}/test`, { method: "POST" }),
  },
  knowledge: {
    upload: (projectId: string, file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      return fetch(`${BASE_URL}/api/v1/projects/${projectId}/knowledge/upload`, { method: "POST", body: formData, headers: authHeaders() }).then(r => r.json())
    },
    clearVector: (projectId: string) => request<void>(`/api/v1/projects/${projectId}/knowledge/clear-vector`, { method: "DELETE" }),
  },
  generate: {
    architecture: (projectId: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/architecture`)),
    blueprint: (projectId: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/blueprint`)),
    chapter: (projectId: string, num: number) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/chapter/${num}`)),
    finalize: (projectId: string, num: number) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/finalize/${num}`)),
  },
  characters: {
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/characters`),
    create: (projectId: string, data: { name: string; description?: string }) => request<any>(`/api/v1/projects/${projectId}/characters`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, charId: number, data: any) => request<any>(`/api/v1/projects/${projectId}/characters/${charId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, charId: number) => request<void>(`/api/v1/projects/${projectId}/characters/${charId}`, { method: "DELETE" }),
    importFromState: (projectId: string) => request<any>(`/api/v1/projects/${projectId}/characters/import-from-state`, { method: "POST" }),
  },
  export: {
    download: (projectId: string, format: "txt" | "html" = "txt") => {
      window.open(sseUrl(`/api/v1/projects/${projectId}/export?format=${format}`), "_blank")
    },
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
