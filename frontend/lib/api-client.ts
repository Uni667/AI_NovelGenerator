import { getToken } from "./auth"
import type { 
  Project, ProjectConfig, Chapter, ProjectFile, CharacterProfile,
  CharacterRelationship, CharacterConflict, CharacterAppearance, RelationshipGraph,
  CharacterDashboard, TimelineEntry,
  ApiCredential, ModelProfile, ModelAssignment, KnowledgeFile,
  PlatformHookResult, PlatformTitlesResult, PlatformBlurbResult, PlatformTagsResult, PlatformDiagnosisResult,
  MaterialEntity, DiagnosisReport, PromptMeta, PromptEntry, ProjectAnalytics,
  VisualizerCharacter, VisualizerScene, VisualizerEvent, VisualizerData, VisualizerRelationship,
  EmotionAnalysis, EmotionArcPoint, EmotionArcSummary,
  LocalLibraryConfig, LocalReferenceBook, LocalReferenceChapter,
  ProjectReferenceBinding, LocalAbsorptionTask, ScanReport
} from "./types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

const KNOWN_ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: "请先登录。",
  PROJECT_NOT_FOUND: "项目不存在或你没有权限访问。",
  PROJECT_FORBIDDEN: "项目不存在或你没有权限访问。",
  API_CREDENTIAL_IN_USE: "这个模型服务账号正在被模型配置使用。你可以选择同时删除关联模型配置。",
  API_CREDENTIAL_DISABLED: "API Key 尚未通过测试。",
  API_KEY_DECRYPT_FAILED: "API Key 读取失败，请重新填写后再试。",
  API_KEY_INVALID: "测试失败，请检查 API Key 和服务商是否匹配。",
  BASE_URL_INVALID: "服务地址配置异常，请点击修复旧配置或清空后重配。",
  MODEL_NAME_INVALID: "模型名配置异常，请清空后重新配置。",
  MODEL_CONFIG_INVALID: "当前模型配置不完整，建议清空后重新配置。",
  MODEL_CONFIG_INCOMPLETE: "当前模型配置不完整，建议清空后重新配置。",
  MODEL_PROFILE_NOT_FOUND: "你还没有配置文本生成模型，请先完成模型设置。",
  MODEL_TYPE_MISMATCH: "当前阶段选择的模型类型不匹配。",
  SERVER_INTERFACE_NOT_FOUND: "服务器接口未找到，请重新部署后再试。",
  reason_required: "请填写修改原因，方便后续从审计日志中追踪。",
  high_risk_required: "该操作会影响人物真实姓名、身份、称呼规则或主线事实，需要勾选高风险确认后才能保存。",
  JSONDecodeError: "解析 JSON 数据失败，请检查输入格式是否正确。",
  ConfigError: "系统配置错误，请检查项目设置或模型配置。",
  validation_failed: "输入数据未通过验证，请检查内容是否符合要求。",
  patch_failed: "补丁处理失败，请稍后再试或废弃此补丁。",
  outline_diff_failed: "大纲演化差异应用失败，请手动修正大纲冲突。",
  memory_file_missing: "关键状态文件丢失，系统将使用默认空状态或自动恢复。",
  memory_file_corrupted: "状态文件格式损坏，系统已停止写入以保护项目。请前往备份页恢复最近一次可用备份。",
  backup_restore_failed: "备份恢复失败，请检查备份文件是否完整。",
  generation_context_failed: "本章状态上下文构建失败，系统已回退到基础生成逻辑。",
}

class ApiError extends Error {
  code?: string
  details?: Record<string, unknown>
  status?: number

  constructor(message: string, code?: string, details?: Record<string, unknown>, status?: number) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.details = details
    this.status = status
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

function sanitizeMessage(message: string, status?: number): string {
  const text = (message || "").trim()
  if (status === 404) return "服务器接口未找到，请重新部署后再试。"
  if (!text) return "请求失败，请稍后重试。"
  if (text.startsWith("<") || text.includes("Traceback") || text.includes("stack") || text.length > 180) {
    return "请求失败，请稍后重试。"
  }
  if (text.includes("API Key") && (text.includes("sk-") || text.length > 80)) {
    return "测试失败，请检查 API Key 和服务商是否匹配。"
  }
  if (text.includes("模型名") && text.includes("URL")) return "模型名配置异常，请清空后重新配置。"
  if (text.includes("Base URL") || text.includes("baseUrl")) return "服务地址配置异常，请点击修复旧配置或清空后重配。"
  if (text.includes("被") && text.includes("模型配置") && text.includes("引用")) {
    return "这个模型服务账号正在被模型配置使用。你可以选择同时删除关联模型配置。"
  }
  if (text.includes("high_risk_required")) return "该操作会影响核心设定，需要勾选高风险确认后才能保存。"
  if (text.includes("reason_required")) return "请填写修改原因，方便后续从审计日志中追踪。"
  if (text.includes("JSONDecodeError")) return "解析 JSON 数据失败，请检查输入格式是否正确。"
  if (text.includes("memory_file_corrupted")) return "状态文件格式损坏，系统已停止写入以保护项目。请前往备份页恢复最近一次可用备份。"
  if (text.includes("generation_context_failed")) return "本章状态上下文构建失败，系统已回退到基础生成逻辑。"
  return text
}

function formatErrorDetail(detail: unknown, status?: number): { message: string; code?: string; details?: Record<string, unknown> } {
  if (Array.isArray(detail)) {
    const message = detail
      .map((item: any) => {
        const loc = Array.isArray(item?.loc) ? item.loc.join(".") : ""
        const msg = item?.msg || "参数格式不正确。"
        return loc ? `${loc}: ${msg}` : msg
      })
      .join("; ")
    return { message: sanitizeMessage(message, status) }
  }
  if (detail && typeof detail === "object") {
    const value = detail as { message?: string; error?: { message?: string; code?: string; details?: Record<string, unknown> }; code?: string; details?: Record<string, unknown> }
    const code = value.error?.code || value.code
    const details = value.error?.details || value.details
    if (code && KNOWN_ERROR_MESSAGES[code]) return { message: KNOWN_ERROR_MESSAGES[code], code, details }
    return { message: sanitizeMessage(value.error?.message || value.message || "请求失败，请稍后重试。", status), code, details }
  }
  return { message: typeof detail === "string" ? sanitizeMessage(detail, status) : "" }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const method = options?.method || "GET"
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${url}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
    })
  } catch (error: any) {
    throw new ApiError("无法连接到后端服务，请检查网络或确认后端服务已启动。", "NETWORK_ERROR", undefined, 0)
  }
  if (!res.ok) {
    let message = res.statusText
    let code: string | undefined
    let details: Record<string, unknown> | undefined
    try {
      const body = await res.json()
      const formatted = formatErrorDetail(body.detail, res.status)
      message = formatted.message || sanitizeMessage(body.message || message, res.status)
      code = formatted.code
      details = formatted.details
    } catch {
      message = sanitizeMessage("", res.status)
    }
    if (res.status === 401 && typeof window !== "undefined") {
      const { clearToken } = await import("./auth")
      clearToken()
      // 不在此处硬刷新，由 AuthGuard 统一处理路由跳转，避免刷新循环
    }
    throw new ApiError(message || `请求失败：${method} ${url} (${res.status})`, code, details, res.status)
  }
  const contentType = res.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    return res.json()
  }
  return (await res.text()) as unknown as T
}

function sseUrl(path: string, taskId?: string, extraParams?: Record<string, string>): string {
  const url = new URL(`${BASE_URL}${path}`)
  if (taskId) {
    url.searchParams.append("task_id", taskId)
  }
  if (extraParams) {
    Object.entries(extraParams).forEach(([k, v]) => {
      if (v) url.searchParams.append(k, v)
    })
  }
  return url.toString()
}

export const api = {
  client: {
    get: (url: string) => request<any>(url).then(data => ({ data })),
    post: (url: string, body?: any) => request<any>(url, { method: "POST", body: JSON.stringify(body) }).then(data => ({ data })),
    put: (url: string, body?: any) => request<any>(url, { method: "PUT", body: JSON.stringify(body) }).then(data => ({ data })),
    patch: (url: string, body?: any) => request<any>(url, { method: "PATCH", body: JSON.stringify(body) }).then(data => ({ data })),
    delete: (url: string) => request<any>(url, { method: "DELETE" }).then(data => ({ data })),
  },
  health: {
    check: () => request<{ status: string; service: string }>("/api/v1/health"),
  },
  projects: {
    list: () => request<Project[]>("/api/v1/projects"),
    get: (id: string) => request<Project>(`/api/v1/projects/${id}`),
    create: (data: Partial<Project> & Record<string, any>) => request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Project>) => request<Project>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
    config: (id: string) => request<ProjectConfig>(`/api/v1/projects/${id}/config`),
    updateConfig: (id: string, data: Partial<ProjectConfig>) => request<ProjectConfig>(`/api/v1/projects/${id}/config`, { method: "PUT", body: JSON.stringify(data) }),
    inferConfig: (data: { user_guidance: string; platform: string }) => request<{ success: boolean; data: any }>("/api/v1/projects/infer-config", { method: "POST", body: JSON.stringify(data) }),
    backupUrl: (id: string) => `${BASE_URL}/api/v1/projects/${id}/backup`,
    importBackup: (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      return fetch(`${BASE_URL}/api/v1/projects/import-backup`, {
        method: "POST",
        body: formData,
        headers: authHeaders(),
      }).then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail || "导入备份失败")
        }
        return res.json()
      })
    },
    importLocalFolder: (folderPath: string, projectName?: string, platform?: string, genre?: string) =>
      request<{ message: string; projectId: string; name: string }>("/api/v1/projects/import-local-folder", {
        method: "POST",
        body: JSON.stringify({ folder_path: folderPath, project_name: projectName, platform, genre }),
      }),
    exportLocalFolder: (projectId: string, folderPath: string) =>
      request<{ success: boolean; message: string; path: string }>(`/api/v1/projects/${projectId}/export-local-folder`, {
        method: "POST",
        body: JSON.stringify({ folder_path: folderPath }),
      }),
  },
  chapters: {
    list: (projectId: string) => request<Chapter[]>(`/api/v1/projects/${projectId}/chapters`),
    get: (projectId: string, num: number) => request<{ chapter_number: number, content: string, meta: Chapter }>(`/api/v1/projects/${projectId}/chapters/${num}`),
    update: (projectId: string, num: number, data: Partial<Chapter & {content: string; status?: string}>) => request<{ meta: Chapter }>(`/api/v1/projects/${projectId}/chapters/${num}`, { method: "PUT", body: JSON.stringify(data) }),
    copy: (projectId: string, num: number) => request<{ message: string; meta: Chapter }>(`/api/v1/projects/${projectId}/chapters/${num}/copy`, { method: "POST" }),
    delete: (projectId: string, num: number) => request<{ message: string; chapter_number: number }>(`/api/v1/projects/${projectId}/chapters/${num}`, { method: "DELETE" }),
    syncSubsequent: (projectId: string, num: number) => request<{ message: string; chapters: Chapter[] }>(`/api/v1/projects/${projectId}/chapters/${num}/sync-subsequent`, { method: "POST" }),
    askAi: (projectId: string, num: number, question: string, selectedText?: string) => 
      new EventSource(sseUrl(`/api/v1/projects/${projectId}/chapters/${num}/ask-ai`, undefined, {
        question,
        ...(selectedText ? { selected_text: selectedText } : {})
      })),
    upload: (projectId: string, files: File[]) => {
      const formData = new FormData()
      files.forEach((f) => formData.append("files", f))
      return fetch(`${BASE_URL}/api/v1/projects/${projectId}/chapters/upload`, {
        method: "POST",
        body: formData,
        headers: authHeaders(),
      }).then(async (res) => {
        if (!res.ok) {
          let message = res.statusText
          try {
            const body = await res.json()
            const formatted = formatErrorDetail(body.detail, res.status)
            message = formatted.message || sanitizeMessage(body.message || message, res.status)
          } catch {
            message = sanitizeMessage("", res.status)
          }
          throw new Error(`批量上传失败: ${message}`)
        }
        return res.json()
      })
    },
    generate: (projectId: string, chapterNumber: number, customPromptText?: string, startStep?: string) => 
      request<{ success: boolean, task_id: string }>(`/api/v1/projects/${projectId}/chapters/${chapterNumber}/generate`, {
        method: "POST",
        body: JSON.stringify({
          custom_prompt_text: customPromptText,
          start_step: startStep
        })
      }),
    getSimilarityReport: (projectId: string, chapterNumber: number) =>
      request<any>(`/api/v1/projects/${projectId}/chapters/${chapterNumber}/similarity-report`),
  },
  files: {
    get: (projectId: string, filename: string) => request<string>(`/api/v1/projects/${projectId}/files/${encodeURIComponent(filename)}`),
    delete: (projectId: string, filename: string) => request<{ message: string; filename: string }>(`/api/v1/projects/${projectId}/files/${encodeURIComponent(filename)}`, { method: "DELETE" }),
  },
  config: {
    // API 凭证
    listCredentials: () => request<ApiCredential[]>("/api/v1/user/api-credentials"),
    createCredential: (data: { name: string; provider: string; api_key: string; base_url: string; is_default?: boolean }) =>
      request<ApiCredential>("/api/v1/user/api-credentials", { method: "POST", body: JSON.stringify(data) }),
    updateCredential: (id: string, data: Partial<ApiCredential>) =>
      request<ApiCredential>(`/api/v1/user/api-credentials/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteCredential: (id: string, cascade?: boolean) =>
      request<void>(`/api/v1/user/api-credentials/${id}${cascade ? "?cascade=true" : ""}`, { method: "DELETE" }),
    testCredential: (id: string) =>
      request<{ success: boolean; message: string }>(`/api/v1/user/api-credentials/${id}/test`, { method: "POST" }),
    revealCredentialKey: (id: string) =>
      request<{ api_key: string }>(`/api/v1/user/api-credentials/${id}/reveal-key`),
    enableCredential: (id: string) =>
      request<any>(`/api/v1/user/api-credentials/${id}/enable`, { method: "POST" }),
    disableCredential: (id: string) =>
      request<any>(`/api/v1/user/api-credentials/${id}/disable`, { method: "POST" }),
    fetchModels: (id: string) =>
      request<{ models: { id: string; name: string; type: string; provider: string }[]; provider: string }>(`/api/v1/user/api-credentials/${id}/models`),
    fixLegacyCredentials: () =>
      request<{ fixed: number; details: any[] }>("/api/v1/user/fix-legacy-credentials", { method: "POST" }),
    modelQuickSetup: (data: { provider: string; api_key: string; project_id?: string }) =>
      request<{ success: boolean; data: { message: string; provider: string; chatReady: boolean; embeddingReady: boolean; chatModel: string; embeddingMessage: string } }>("/api/v1/user/model-quick-setup", { method: "POST", body: JSON.stringify(data) }),
    modelStatus: () =>
      request<{ chatReady: boolean; coreReady: boolean; embeddingReady: boolean; embeddingMessage?: string; state?: "empty" | "invalid" | "ready"; title?: string; description?: string; message?: string; provider?: string; providerLabel?: string; chatProvider?: string; chatModel?: string; lastTestedAt?: string; recentTestedAt?: string; chatErrors?: string[]; activeCredentials?: number; hasCredential?: boolean; hasChatProfile?: boolean }>("/api/v1/user/model-settings/status"),
    modelReset: () =>
      request<{ success: boolean; message: string }>("/api/v1/user/model-settings/reset", { method: "POST" }),
    modelRepair: () =>
      request<{ success: boolean; message: string; details: string[] }>("/api/v1/user/model-settings/repair", { method: "POST" }),
    // 模型配置
    listProfiles: () => request<ModelProfile[]>("/api/v1/user/model-profiles"),
    getProfile: (id: string) => request<ModelProfile>(`/api/v1/user/model-profiles/${id}`),
    createProfile: (data: Partial<ModelProfile>) =>
      request<ModelProfile>("/api/v1/user/model-profiles", { method: "POST", body: JSON.stringify(data) }),
    updateProfile: (id: string, data: Partial<ModelProfile>) =>
      request<ModelProfile>(`/api/v1/user/model-profiles/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteProfile: (id: string) =>
      request<void>(`/api/v1/user/model-profiles/${id}`, { method: "DELETE" }),
    testProfile: (id: string) =>
      request<{ success: boolean; message: string }>(`/api/v1/user/model-profiles/${id}/test`, { method: "POST" }),
    setDefaultProfile: (id: string) =>
      request<any>(`/api/v1/user/model-profiles/${id}/set-default`, { method: "POST" }),
    // 调用日志
    listInvocationLogs: (limit?: number) =>
      request<any[]>(`/api/v1/user/model-invocation-logs?limit=${limit || 50}`),
    listProjectInvocationLogs: (projectId: string, limit?: number) =>
      request<any[]>(`/api/v1/projects/${projectId}/model-invocation-logs?limit=${limit || 30}`),
  },
  modelAssignment: {
    get: (projectId: string) => request<ModelAssignment>(`/api/v1/projects/${projectId}/model-assignment`),
    save: (projectId: string, data: ModelAssignment) =>
      request<ModelAssignment>(`/api/v1/projects/${projectId}/model-assignment`, { method: "PUT", body: JSON.stringify(data) }),
    applyPlatformPreset: (projectId: string, platform: string) =>
      request<ModelAssignment>(`/api/v1/projects/${projectId}/model-assignment/apply-platform-preset`, { method: "POST", body: JSON.stringify({ platform }) }),
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
            const formatted = formatErrorDetail(body.detail, res.status)
            message = formatted.message || sanitizeMessage(body.message || message, res.status)
          } catch {
            message = sanitizeMessage("", res.status)
          }
          throw new Error(`知识库上传失败: ${message}`)
        }
        return res.json()
      })
    },
    list: (projectId: string) => request<KnowledgeFile[]>(`/api/v1/projects/${projectId}/knowledge/files`),
    delete: (projectId: string, fileId: number) => request<void>(`/api/v1/projects/${projectId}/knowledge/files/${fileId}`, { method: "DELETE" }),
    reimport: (projectId: string, fileId: number) => request<KnowledgeFile>(`/api/v1/projects/${projectId}/knowledge/files/${fileId}/reimport`, { method: "POST" }),
    clearVector: (projectId: string) => request<void>(`/api/v1/projects/${projectId}/knowledge/clear-vector`, { method: "DELETE" }),
    getGraph: (projectId: string) => request<{ nodes: any[]; links: any[] }>(`/api/v1/projects/${projectId}/graph`),
    addNode: (projectId: string, node: { id: string; group: string }) => request<void>(`/api/v1/projects/${projectId}/graph/node`, { method: "POST", body: JSON.stringify(node) }),
    deleteNode: (projectId: string, nodeId: string) => request<void>(`/api/v1/projects/${projectId}/graph/node/${encodeURIComponent(nodeId)}`, { method: "DELETE" }),
    addRelation: (projectId: string, relation: { source: string; target: string; label: string; source_type?: string; target_type?: string }) => request<void>(`/api/v1/projects/${projectId}/graph/relation`, { method: "POST", body: JSON.stringify(relation) }),
    deleteRelation: (projectId: string, source: string, target: string) => request<void>(`/api/v1/projects/${projectId}/graph/relation?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`, { method: "DELETE" }),
  },
  generate: {
    architecture: (projectId: string, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/architecture`, taskId)),
    blueprint: (projectId: string, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/blueprint`, taskId)),
    chapter: (projectId: string, num: number, taskId?: string, startStep?: string, enableBrainstorming?: boolean) => 
      new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/chapter/${num}`, taskId, {
        ...(startStep ? { start_step: startStep } : {}),
        ...(enableBrainstorming ? { enable_brainstorming: "true" } : {})
      })),
    chapterBatch: (projectId: string, startChapter: number, count: number, taskId?: string, startStep?: string, enableBrainstorming?: boolean) => 
      new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/chapters`, taskId, { 
        start_chapter: startChapter.toString(), 
        count: count.toString(), 
        ...(startStep ? { start_step: startStep } : {}),
        ...(enableBrainstorming ? { enable_brainstorming: "true" } : {})
      })),
    finalize: (projectId: string, num: number, taskId?: string) => new EventSource(sseUrl(`/api/v1/projects/${projectId}/generate/finalize/${num}`, taskId)),
    taskStatus: (projectId: string, taskId: string) => request<any>(`/api/v1/projects/${projectId}/generate/tasks/${taskId}`),
    cancelTask: (projectId: string, taskId: string) => request<any>(`/api/v1/projects/${projectId}/generate/tasks/${taskId}/cancel`, { method: "POST" }),
    retryTask: (projectId: string, taskId: string) => request<any>(`/api/v1/projects/${projectId}/generate/tasks/${taskId}/retry`, { method: "POST" }),
    listTasks: (projectId: string) => request<any[]>(`/api/v1/projects/${projectId}/generate/tasks`),
  },
  characters: {
    list: (projectId: string) => request<CharacterProfile[]>(`/api/v1/projects/${projectId}/characters`),
    create: (projectId: string, data: { name: string; description?: string; status?: string; source?: string; first_appearance_chapter?: number | null }) => request<CharacterProfile>(`/api/v1/projects/${projectId}/characters`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, charId: number, data: Partial<CharacterProfile>) => request<CharacterProfile>(`/api/v1/projects/${projectId}/characters/${charId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, charId: number) => request<void>(`/api/v1/projects/${projectId}/characters/${charId}`, { method: "DELETE" }),
    importPreview: (projectId: string) => request<{ summary: any; candidates: CharacterProfile[] }>(`/api/v1/projects/${projectId}/characters/import-from-state/preview`, { method: "POST" }),
    importFromState: (projectId: string, data?: { selected_candidate_ids: string[] }) => request<CharacterProfile[]>(`/api/v1/projects/${projectId}/characters/import-from-state`, { method: "POST", body: JSON.stringify(data || {}) }),
    suggest: (projectId: string) => request<{ characters: CharacterProfile[] }>(`/api/v1/projects/${projectId}/characters/suggest`, { method: "POST" }),
    plan: (projectId: string) => request<{ characters: CharacterProfile[]; outline?: string }>(`/api/v1/projects/${projectId}/characters/plan`, { method: "POST" }),
    refreshFromFile: (projectId: string) => request<CharacterProfile[]>(`/api/v1/projects/${projectId}/characters/refresh-from-file`, { method: "POST" }),
    dashboard: (projectId: string) => request<CharacterDashboard>(`/api/v1/projects/${projectId}/characters/dashboard`),
  },
  characterRelationships: {
    list: (projectId: string) => request<CharacterRelationship[]>(`/api/v1/projects/${projectId}/character-relationships`),
    create: (projectId: string, data: Partial<CharacterRelationship>) => request<CharacterRelationship>(`/api/v1/projects/${projectId}/character-relationships`, { method: "POST", body: JSON.stringify(data) }),
    createBatch: (projectId: string, data: Partial<CharacterRelationship>[]) => request<{ created: number; ids: number[] }>(`/api/v1/projects/${projectId}/character-relationships/batch`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, relId: number, data: Partial<CharacterRelationship>) => request<CharacterRelationship>(`/api/v1/projects/${projectId}/character-relationships/${relId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, relId: number) => request<void>(`/api/v1/projects/${projectId}/character-relationships/${relId}`, { method: "DELETE" }),
    graph: (projectId: string) => request<RelationshipGraph>(`/api/v1/projects/${projectId}/character-relationships/graph`),
    types: () => request<{ types: { value: string; label: string }[]; statuses: string[] }>(`/api/v1/character-relationship-types`),
  },
  characterConflicts: {
    list: (projectId: string) => request<CharacterConflict[]>(`/api/v1/projects/${projectId}/character-conflicts`),
    create: (projectId: string, data: Partial<CharacterConflict>) => request<CharacterConflict>(`/api/v1/projects/${projectId}/character-conflicts`, { method: "POST", body: JSON.stringify(data) }),
    createBatch: (projectId: string, data: Partial<CharacterConflict>[]) => request<{ created: number; ids: number[] }>(`/api/v1/projects/${projectId}/character-conflicts/batch`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, conflictId: number, data: Partial<CharacterConflict>) => request<CharacterConflict>(`/api/v1/projects/${projectId}/character-conflicts/${conflictId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, conflictId: number) => request<void>(`/api/v1/projects/${projectId}/character-conflicts/${conflictId}`, { method: "DELETE" }),
    types: () => request<{ types: { value: string; label: string }[]; statuses: string[] }>(`/api/v1/character-conflict-types`),
  },
  characterAppearances: {
    list: (projectId: string, params?: { character_id?: number; chapter_number?: number }) => {
      let url = `/api/v1/projects/${projectId}/character-appearances`
      if (params?.character_id) url += `?character_id=${params.character_id}`
      else if (params?.chapter_number) url += `?chapter_number=${params.chapter_number}`
      return request<CharacterAppearance[]>(url)
    },
    create: (projectId: string, data: Partial<CharacterAppearance>) => request<CharacterAppearance>(`/api/v1/projects/${projectId}/character-appearances`, { method: "POST", body: JSON.stringify(data) }),
    createBatch: (projectId: string, data: Partial<CharacterAppearance>[]) => request<{ created: number; ids: number[] }>(`/api/v1/projects/${projectId}/character-appearances/batch`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, appearanceId: number, data: Partial<CharacterAppearance>) => request<CharacterAppearance>(`/api/v1/projects/${projectId}/character-appearances/${appearanceId}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (projectId: string, appearanceId: number) => request<void>(`/api/v1/projects/${projectId}/character-appearances/${appearanceId}`, { method: "DELETE" }),
    timeline: (projectId: string) => request<TimelineEntry[]>(`/api/v1/projects/${projectId}/character-appearances/timeline`),
    types: () => request<{ types: { value: string; label: string }[]; statuses: string[] }>(`/api/v1/character-appearance-types`),
  },
  export: {
    download: async (projectId: string, format: "txt" | "html" = "txt") => {
      const win = window.open("", "_blank")
      if (!win) return
      try {
        const res = await request<{ stream_token: string }>("/api/v1/auth/stream-token", { method: "POST" })
        const url = new URL(`${BASE_URL}/api/v1/projects/${projectId}/export`)
        url.searchParams.append("format", format)
        url.searchParams.append("token", res.stream_token)
        win.location.href = url.toString()
      } catch (err) {
        win.close()
        console.error("下载失败", err)
      }
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
            const formatted = formatErrorDetail(body.detail, res.status)
            message = formatted.message || sanitizeMessage(body.message || message, res.status)
          } catch {
            message = sanitizeMessage("", res.status)
          }
          throw new Error(`导入失败: ${message}`)
        }
        return res.json()
      })
    },
    list: (projectId: string, fileType?: string) => {
      const qs = fileType ? `?type=${encodeURIComponent(fileType)}` : ""
      return request<ProjectFile[]>(`/api/v1/projects/${projectId}/project-files${qs}`)
    },
    setCurrent: (projectId: string, fileId: string) =>
      request<ProjectFile>(`/api/v1/projects/${projectId}/project-files/${fileId}/set-current`, { method: "PUT" }),
    getCurrentArchitecture: (projectId: string) =>
      request<ProjectFile>(`/api/v1/projects/${projectId}/current-architecture`).catch(() => null),
    getCurrentOutline: (projectId: string) =>
      request<ProjectFile>(`/api/v1/projects/${projectId}/current-outline`).catch(() => null),
    delete: (projectId: string, fileId: string) =>
      request<{ message: string }>(`/api/v1/projects/${projectId}/project-files/${fileId}`, { method: "DELETE" }),
  },
  platform: {
    titles: (projectId: string) => request<PlatformTitlesResult>(`/api/v1/projects/${projectId}/tools/titles`, { method: "POST" }),
    blurb: (projectId: string) => request<PlatformBlurbResult>(`/api/v1/projects/${projectId}/tools/blurb`, { method: "POST" }),
    hookCheck: (projectId: string, chapterNumber = 1) => request<{ analysis: PlatformHookResult }>(`/api/v1/projects/${projectId}/tools/hook-check?chapter_number=${chapterNumber}`, { method: "POST" }),
    chapterHookCheck: (projectId: string, chapterNumber: number) => request<{ analysis: PlatformHookResult }>(`/api/v1/projects/${projectId}/tools/chapter-hook-check?chapter_number=${chapterNumber}`, { method: "POST" }),
    batchHookCheck: (projectId: string) => request<{ chapters: { chapter_number: number, analysis: PlatformHookResult }[] }>(`/api/v1/projects/${projectId}/tools/batch-hook-check`, { method: "POST" }),
    tags: (projectId: string) => request<PlatformTagsResult>(`/api/v1/projects/${projectId}/tools/tags`, { method: "POST" }),
    chapterTitle: (projectId: string, chapterNumber: number) => request<PlatformTitlesResult>(`/api/v1/projects/${projectId}/tools/chapter-title?chapter_number=${chapterNumber}`, { method: "POST" }),
    diagnose: (projectId: string, chapterNumber: number) => request<PlatformDiagnosisResult>(`/api/v1/projects/${projectId}/tools/diagnose?chapter_number=${chapterNumber}`, { method: "POST" }),
    diagnoseAndFix: (projectId: string, data: { chapter_number: number; chapter_content: string; diagnosis: string; selected_issues: string[] }) => { const url = `${BASE_URL}/api/v1/projects/${projectId}/tools/diagnose-and-fix`; return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(data) }); },
    commercialGenerate: (projectId: string, params: Record<string, any>) => request<{ mode: string; result: string; platform: string }>(`/api/v1/projects/${projectId}/tools/commercial-generate?${new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])).toString()}`, { method: "POST" }),
    profiles: () => request<{ platforms: Record<string, any>; trends: Record<string, any> }>(`/api/v1/platform/profiles`),
  },
  materials: {
    decompose: (projectId: string, rawText: string) => 
      request<{ entities: MaterialEntity[] }>(`/api/v1/projects/${projectId}/materials/decompose`, { 
        method: "POST", 
        body: JSON.stringify({ raw_text: rawText }) 
      }),
    diagnose: (projectId: string, entity: MaterialEntity) => 
      request<{ diagnosis: DiagnosisReport }>(`/api/v1/projects/${projectId}/materials/diagnose`, { 
        method: "POST", 
        body: JSON.stringify({ entity }) 
      }),
    optimize: (projectId: string, entity: MaterialEntity, diagnosis: DiagnosisReport, userInstruction: string = "") => 
      request<{ optimized_content: string }>(`/api/v1/projects/${projectId}/materials/optimize`, { 
        method: "POST", 
        body: JSON.stringify({ entity, diagnosis, user_instruction: userInstruction }) 
      }),
    sync: (projectId: string, entities: MaterialEntity[]) => 
      request<{ message: string; characters_added: number; others_added: number }>(`/api/v1/projects/${projectId}/materials/sync`, { 
        method: "POST", 
        body: JSON.stringify({ entities }) 
      }),
  },

  prompts: {
    keys: () =>
      request<{ prompts: PromptMeta[] }>(`/api/v1/prompts/keys`),
    list: (projectId: string) =>
      request<{ prompts: PromptEntry[] }>(`/api/v1/projects/${projectId}/prompts`),
    update: (projectId: string, key: string, content: string) =>
      request<{ message: string; key: string; is_overridden: boolean }>(`/api/v1/projects/${projectId}/prompts/${key}`, {
        method: "PUT",
        body: JSON.stringify({ content }),
      }),
    reset: (projectId: string, key: string) =>
      request<{ message: string; key: string; is_overridden: boolean }>(`/api/v1/projects/${projectId}/prompts/${key}`, {
        method: "DELETE",
      }),
    snapshots: (projectId: string, key: string) =>
      request<{ snapshots: { id: string; timestamp: number; readable_time: string; preview: string; content: string }[] }>(`/api/v1/projects/${projectId}/prompts/${key}/snapshots`),
    restore: (projectId: string, key: string, snapshotId: string) =>
      request<{ message: string; key: string; content: string }>(`/api/v1/projects/${projectId}/prompts/${key}/restore`, {
        method: "POST",
        body: JSON.stringify({ snapshot_id: snapshotId }),
      }),
    export: (projectId: string) =>
      request<{ custom_prompts: Record<string, string> }>(`/api/v1/projects/${projectId}/prompts/export`),
    import: (projectId: string, customPrompts: Record<string, string>) =>
      request<{ message: string }>(`/api/v1/projects/${projectId}/prompts/import`, {
        method: "POST",
        body: JSON.stringify({ custom_prompts: customPrompts }),
      }),
  },

  interactive: {
    getRewriteUrl: (projectId: string) => `${BASE_URL}/api/v1/projects/${projectId}/interactive/rewrite`,
  },

  plotArcs: {
    get: (projectId: string) => request<{ content: string }>(`/api/v1/projects/${projectId}/plot_arcs`),
    update: (projectId: string, content: string) => request<{ message: string }>(`/api/v1/projects/${projectId}/plot_arcs`, { method: "PUT", body: JSON.stringify({ content }) }),
  },

  analytics: {
    get: (projectId: string) =>
      request<ProjectAnalytics>(`/api/v1/projects/${projectId}/analytics`),
  },
  visualizer: {
    getData: (projectId: string) =>
      request<VisualizerData>(
        `/api/v1/projects/${projectId}/visualizer/data`
      ),
    analyzeChapters: (projectId: string, chapterNumber?: number) => 
      request<{ parsed_chapters: number[]; new_characters_count: number; new_scenes_count: number; new_events_count: number }>(
        `/api/v1/projects/${projectId}/visualizer/analyze-chapters${chapterNumber !== undefined ? `?chapter_number=${chapterNumber}` : ""}`,
        { method: "POST", body: JSON.stringify({}) }
      ),
    generatePrompt: (projectId: string, type: 'character' | 'scene' | 'event', id: string) =>
      request<{ prompt: string }>(
        `/api/v1/projects/${projectId}/visualizer/generate-prompt`,
        { method: "POST", body: JSON.stringify({ type, id }) }
      ),
    updateCharacter: (projectId: string, charId: string, payload: Partial<VisualizerCharacter>) =>
      request<VisualizerCharacter>(
        `/api/v1/projects/${projectId}/visualizer/characters/${charId}`,
        { method: "PUT", body: JSON.stringify(payload) }
      ),
    getCharacterDetails: (projectId: string, charId: string) =>
      request<VisualizerCharacter>(
        `/api/v1/projects/${projectId}/visualizer/characters/${charId}`
      ),
    generateAvatar: (projectId: string, charId: string) =>
      request<{ avatarUrl: string }>(
        `/api/v1/projects/${projectId}/visualizer/characters/${charId}/generate-avatar`,
        { method: "POST" }
      ),
  },
  emotion: {
    analyzeChapter: (projectId: string, chapterNumber: number, method: string = "snownlp") =>
      request<{ project_id: string; chapter_number: number; char_count: number; analysis: EmotionAnalysis }>(
        `/api/v1/projects/${projectId}/chapters/${chapterNumber}/emotion`,
        { method: "POST", body: JSON.stringify({ method }) }
      ),
    getArc: (projectId: string, method: string = "snownlp") =>
      request<{ arc: EmotionArcPoint[]; summary: EmotionArcSummary; method: string }>(
        `/api/v1/projects/${projectId}/emotion-arc?method=${method}`
      ),
    quickAnalyze: (text: string, method: string = "snownlp") =>
      request<{ analysis: EmotionAnalysis; char_count: number }>(
        `/api/v1/emotion/quick-analyze`,
        { method: "POST", body: JSON.stringify({ text, method }) }
      ),
  },
  auth: {
    streamToken: () => request<{ stream_token: string }>("/api/v1/auth/stream-token", { method: "POST" }),
  },
  migration: {
    exportAll: (token?: string) => {
      const headers: Record<string, string> = {};
      if (token) {
        headers["X-Migration-Token"] = token;
      }
      return request<any>("/api/v1/migration/export-all", { headers });
    },
  },
  localLibrary: {
    getConfig: () => request<LocalLibraryConfig>("/api/v1/local-library/config"),
    updateConfig: (data: Partial<LocalLibraryConfig>) =>
      request<LocalLibraryConfig>("/api/v1/local-library/config", { method: "PUT", body: JSON.stringify(data) }),
    testConfig: (data: Partial<LocalLibraryConfig>) =>
      request<{ source_dir: any; essence_dir: any; success: boolean }>("/api/v1/local-library/config/test", { method: "POST", body: JSON.stringify(data) }),
    scan: () => request<ScanReport>("/api/v1/local-library/scan", { method: "POST" }),
    listBooks: () => request<LocalReferenceBook[]>("/api/v1/local-library/books"),
    getBook: (bookId: string) => request<LocalReferenceBook>(`/api/v1/local-library/books/${bookId}`),
    parseBook: (bookId: string) => request<any>(`/api/v1/local-library/books/${bookId}/parse`, { method: "POST" }),
    listChapters: (bookId: string) => request<LocalReferenceChapter[]>(`/api/v1/local-library/books/${bookId}/chapters`),
    updateChapter: (bookId: string, chapterId: string, data: Partial<LocalReferenceChapter>) =>
      request<LocalReferenceChapter>(`/api/v1/local-library/books/${bookId}/chapters/${chapterId}`, { method: "PATCH", body: JSON.stringify(data) }),
    absorb: (bookId: string) => request<LocalAbsorptionTask>(`/api/v1/local-library/books/${bookId}/absorb`, { method: "POST" }),
    getAbsorptionStatus: (bookId: string) => request<LocalAbsorptionTask>(`/api/v1/local-library/books/${bookId}/absorb/status`),
    pauseAbsorb: (bookId: string) => request<any>(`/api/v1/local-library/books/${bookId}/absorb/pause`, { method: "POST" }),
    resumeAbsorb: (bookId: string) => request<any>(`/api/v1/local-library/books/${bookId}/absorb/resume`, { method: "POST" }),
    cancelAbsorb: (bookId: string) => request<any>(`/api/v1/local-library/books/${bookId}/absorb/cancel`, { method: "POST" }),
    getEssenceManifest: (bookId: string) => request<any>(`/api/v1/local-library/books/${bookId}/essence`),
    getEssence: (bookId: string, fileKey: string) => request<any>(`/api/v1/local-library/books/${bookId}/essence/${encodeURIComponent(fileKey)}`),
  },
  projectBindings: {
    list: (projectId: string) => request<ProjectReferenceBinding[]>(`/api/v1/projects/${projectId}/local-reference-books`),
    bind: (projectId: string, bookId: string, data: { book_id: string; enabled?: boolean; weight?: number; use_style_bible?: boolean; use_scene_patterns?: boolean; use_pacing_rules?: boolean; use_character_arcs?: boolean; use_anti_copy_guard?: boolean }) =>
      request<ProjectReferenceBinding>(`/api/v1/projects/${projectId}/local-reference-books/${bookId}/attach`, { method: "POST", body: JSON.stringify(data) }),
    update: (projectId: string, bookId: string, data: any) =>
      request<ProjectReferenceBinding>(`/api/v1/projects/${projectId}/local-reference-books/${bookId}`, { method: "PATCH", body: JSON.stringify(data) }),
    unbind: (projectId: string, bookId: string) =>
      request<any>(`/api/v1/projects/${projectId}/local-reference-books/${bookId}`, { method: "DELETE" }),
    previewContext: (projectId: string) =>
      request<any>(`/api/v1/projects/${projectId}/reference-context/preview`, { method: "POST" }),
  },
}
