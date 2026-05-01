const BASE_URL = "http://localhost:8001"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

// 项目管理
export const api = {
  projects: {
    list: () => request<any[]>("/api/v1/projects"),
    get: (id: string) => request<any>(`/api/v1/projects/${id}`),
    create: (data: any) => request<any>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: any) => request<any>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) => request<any>(`/api/v1/projects/${id}`, { method: "DELETE" }),
    config: (id: string) => request<any>(`/api/v1/projects/${id}/config`),
    updateConfig: (id: string, data: any) => request<any>(`/api/v1/projects/${id}/config`, { method: "PUT", body: JSON.stringify(data) }),
  },
  chapters: {
    list: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/chapters`),
    get: (projectId: string, num: number) => request<any>(`/api/v1/projects/${projectId}/chapters/${num}`),
    update: (projectId: string, num: number, data: any) => request<any>(`/api/v1/projects/${projectId}/chapters/${num}`, { method: "PUT", body: JSON.stringify(data) }),
  },
  files: {
    get: (projectId: string, filename: string) => fetch(`${BASE_URL}/api/v1/projects/${projectId}/files/${filename}`).then(r => r.text()),
  },
  config: {
    llmList: () => request<Record<string, any>>("/api/v1/config/llm"),
    llmCreate: (data: any) => request<any>("/api/v1/config/llm", { method: "POST", body: JSON.stringify(data) }),
    llmUpdate: (name: string, data: any) => request<any>(`/api/v1/config/llm/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(data) }),
    llmDelete: (name: string) => request<any>(`/api/v1/config/llm/${encodeURIComponent(name)}`, { method: "DELETE" }),
    llmTest: (name: string) => request<any>(`/api/v1/config/llm/${encodeURIComponent(name)}/test`, { method: "POST" }),
    embList: () => request<Record<string, any>>("/api/v1/config/embedding"),
    embCreate: (data: any) => request<any>("/api/v1/config/embedding", { method: "POST", body: JSON.stringify(data) }),
    embDelete: (name: string) => request<any>(`/api/v1/config/embedding/${encodeURIComponent(name)}`, { method: "DELETE" }),
    embTest: (name: string) => request<any>(`/api/v1/config/embedding/${encodeURIComponent(name)}/test`, { method: "POST" }),
  },
  knowledge: {
    upload: (projectId: string, file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      return fetch(`${BASE_URL}/api/v1/projects/${projectId}/knowledge/upload`, { method: "POST", body: formData }).then(r => r.json())
    },
    clearVector: (projectId: string) => request<any>(`/api/v1/projects/${projectId}/knowledge/clear-vector`, { method: "DELETE" }),
  },
  generate: {
    architecture: (projectId: string) => new EventSource(`${BASE_URL}/api/v1/projects/${projectId}/generate/architecture`),
    blueprint: (projectId: string) => new EventSource(`${BASE_URL}/api/v1/projects/${projectId}/generate/blueprint`),
    chapter: (projectId: string, num: number) => new EventSource(`${BASE_URL}/api/v1/projects/${projectId}/generate/chapter/${num}`),
    finalize: (projectId: string, num: number) => new EventSource(`${BASE_URL}/api/v1/projects/${projectId}/generate/finalize/${num}`),
  },
}
