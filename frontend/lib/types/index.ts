export interface Project {
  id: string
  name: string
  description: string
  filepath: string
  status: 'draft' | 'generating' | 'ready' | 'archived'
  created_at: string
  updated_at: string
}

export interface ProjectConfig {
  project_id: string
  topic: string
  genre: string
  num_chapters: number
  word_number: number
  user_guidance: string
  language: string
  platform: string
  category: string
  architecture_llm: string
  chapter_outline_llm: string
  prompt_draft_llm: string
  final_chapter_llm: string
  consistency_review_llm: string
  embedding_config: string
}

export const PLATFORM_CONFIG: Record<string, {
  label: string
  icon: string
  categories: string[]
}> = {
  tomato: {
    label: "番茄小说",
    icon: "🍅",
    categories: [
      "玄幻", "都市", "科幻", "仙侠", "悬疑", "历史",
      "言情", "武侠", "轻小说", "游戏", "竞技", "同人",
      "军事", "现实"
    ],
  },
  qidian: {
    label: "起点中文网",
    icon: "📖",
    categories: [
      "玄幻", "奇幻", "武侠", "仙侠", "都市", "现实",
      "历史", "军事", "游戏", "竞技", "科幻", "悬疑",
      "轻小说", "同人"
    ],
  },
  zongheng: {
    label: "纵横中文网",
    icon: "✒️",
    categories: [
      "玄幻", "奇幻", "武侠", "仙侠", "都市", "历史",
      "军事", "科幻", "悬疑", "游戏", "竞技"
    ],
  },
  other: {
    label: "其他平台",
    icon: "🌐",
    categories: [
      "玄幻", "都市", "科幻", "仙侠", "悬疑", "历史",
      "言情", "武侠", "轻小说", "奇幻", "现实"
    ],
  },
}

export const PLATFORMS = Object.keys(PLATFORM_CONFIG) as Array<keyof typeof PLATFORM_CONFIG>

export interface Chapter {
  id: number
  project_id: string
  chapter_number: number
  chapter_title: string
  chapter_role: string
  chapter_purpose: string
  suspense_level: string
  foreshadowing: string
  plot_twist_level: string
  chapter_summary: string
  word_count: number
  status: 'pending' | 'draft' | 'final'
  created_at: string
  updated_at: string
}

export interface ChapterContent {
  chapter_number: number
  content: string
  meta: Chapter | null
}

export interface LLMConfig {
  name: string
  base_url: string
  model_name: string
  temperature: number
  max_tokens: number
  timeout: number
  interface_format: string
  usage: string
  api_key_masked: string
}

export interface EmbeddingConfig {
  name: string
  base_url: string
  model_name: string
  retrieval_k: number
  interface_format: string
  api_key_masked: string
}

export interface SSEProgress {
  step: string
  status: 'running' | 'done'
  message: string
  progress?: number
}

export interface SSEPartial {
  step: string
  content: string
}

export interface SSEGenerationError {
  step: string
  message: string
  task_id?: string
  status?: "failed"
  terminal?: boolean
  error_code?: string
  error_category?: string
  detail?: string
  retryable?: boolean
  provider?: string
  model_name?: string
  base_url?: string
  status_code?: number
  operation?: string
}

// ── 角色相关 ──

export interface CharacterProfile {
  id: number
  project_id: string
  name: string
  description: string
  status: "appeared" | "planned" | "suggested"
  source: "user" | "ai"
  first_appearance_chapter: number | null
  updated_at: string
}

export interface CharacterRelationship {
  id: number
  project_id: string
  character_id_a: number
  character_id_b: number
  name_a: string
  name_b: string
  rel_type: string
  description: string
  strength: number
  direction: string
  start_chapter: number | null
  status: string
  updated_at: string
}

export interface CharacterConflict {
  id: number
  project_id: string
  title: string
  description: string
  conflict_type: string
  intensity: number
  start_chapter: number | null
  resolved_chapter: number | null
  resolution: string
  status: string
  updated_at: string
  participants: ConflictParticipant[]
}

export interface ConflictParticipant {
  pid: number
  character_id: number
  role: string
  name: string
  char_status: string
}

export interface CharacterAppearance {
  id: number
  project_id: string
  character_id: number
  chapter_number: number
  character_name: string
  character_status: string
  appearance_type: string
  role_in_chapter: string
  summary: string
  updated_at: string
}

export interface RelationshipGraph {
  nodes: { id: number; name: string; status: string }[]
  edges: {
    id: number
    source: number
    target: number
    sourceName: string
    targetName: string
    type: string
    strength: number
    direction: string
    status: string
  }[]
}

export interface TimelineEntry {
  chapter_number: number
  character_count: number
  characters: string[]
  entries: CharacterAppearance[]
}

export const RELATIONSHIP_TYPE_LABELS: Record<string, string> = {
  family: "亲属", ally: "盟友", enemy: "敌对", mentor: "师徒",
  lover: "爱慕/情感", interest: "利益绑定", hidden: "隐性关系",
  evolving: "阶段性变化", rival: "竞争/对手", other: "其他",
}

export const CONFLICT_TYPE_LABELS: Record<string, string> = {
  position: "立场冲突", interest: "利益冲突", emotion: "情感冲突",
  power: "权力冲突", misunderstanding: "误会", life_death: "生死冲突",
  ideology: "理念冲突", class: "阶层冲突", betrayal: "背叛", other: "其他",
}

export interface CharacterDashboard {
  characters: CharacterProfile[]
  relationships: CharacterRelationship[]
  conflicts: CharacterConflict[]
  appearances: CharacterAppearance[]
  timeline: TimelineEntry[]
  summary: {
    total_characters: number
    appeared: number
    planned: number
    suggested: number
    total_relationships: number
    active_relationships: number
    total_conflicts: number
    active_conflicts: number
    total_appearances: number
    chapters_with_data: number
  }
}

export const APPEARANCE_TYPE_LABELS: Record<string, string> = {
  present: "登场", mentioned: "被提及", flashback: "闪回",
  implied: "暗示/伏笔", exit: "退场", return: "回归",
  transformation: "重大转变",
}

// ── 项目文件（架构、目录等） ──

export type FileType = "architecture" | "outline" | "core_seed" | "characters" |
  "worldview" | "summary" | "chapter" | "character_state" | "plot_arcs" | "user_upload"

export type FileSource = "ai_generated" | "user_imported" | "user_edited"

export interface ProjectFile {
  id: string
  project_id: string
  type: FileType
  title: string
  filename: string
  content: string
  source: FileSource
  is_current: boolean
  file_size: number
  created_at: string
  updated_at: string
}

export const FILE_SOURCE_LABELS: Record<FileSource, string> = {
  ai_generated: "AI 生成",
  user_imported: "用户导入",
  user_edited: "用户编辑",
}

// ── 生成任务 ──

export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled"

export type TaskType = "generate_architecture" | "generate_outline" |
  "generate_chapter" | "generate_chapter_batch" | "finalize_chapter"

export interface GenerationTask {
  id: string
  project_id: string
  type: TaskType
  status: TaskStatus
  input_snapshot: string
  output_file_id: string | null
  error_message: string | null
  error_code: string | null
  error_category: string | null
  retryable: boolean
  created_at: string
  updated_at: string
  finished_at: string | null
}

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "等待中",
  running: "生成中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
}

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  generate_architecture: "架构生成",
  generate_outline: "章节目录生成",
  generate_chapter: "章节草稿生成",
  generate_chapter_batch: "批量章节生成",
  finalize_chapter: "章节定稿",
}

export interface ProjectOverview {
  project: Project
  has_architecture: boolean
  architecture_source: FileSource | null
  has_outline: boolean
  outline_source: FileSource | null
}
