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
  category: string
  num_chapters: number
  word_number: number
  user_guidance: string
  language: string
  platform: string
  target_reader: string
  reader_direction: string
  trend_key: string
  custom_trend: string
  trend_translation: string
  forbidden: string
  style_requirement: string
}

export const READER_DIRECTIONS = [
  { value: "male", label: "男频" },
  { value: "female", label: "女频" },
  { value: "dual", label: "双强" },
  { value: "shuangwen", label: "爽文" },
  { value: "ensemble", label: "群像" },
  { value: "plot_driven", label: "剧情流" },
  { value: "romance_driven", label: "感情流" },
  { value: "short_drama", label: "短剧向" },
] as const

export const TREND_KEYS = [
  { value: "resource_anxiety", label: "资源焦虑" },
  { value: "rule_pressure", label: "规则压迫" },
  { value: "fairness_anxiety", label: "公平焦虑" },
  { value: "labor_discipline", label: "打工人规训" },
  { value: "ai_humanity", label: "AI/人性焦虑" },
  { value: "female_agency", label: "女性主体性" },
  { value: "anti_involution", label: "反内卷情绪" },
] as const

export const GENERATION_MODES = [
  { value: "generate_chapter", label: "生成新章节" },
  { value: "rewrite_chapter", label: "改写已有章节" },
  { value: "diagnose", label: "诊断章节问题" },
  { value: "outline", label: "生成章节大纲" },
  { value: "volume_outline", label: "生成卷纲" },
  { value: "character_bio", label: "生成角色小传" },
  { value: "platform_opening", label: "生成平台化开篇" },
  { value: "selling_points", label: "生成爽点设计" },
  { value: "ending_hook", label: "生成结尾钩子" },
  { value: "set_piece", label: "生成名场面" },
  { value: "short_drama", label: "生成短剧化分镜" },
  { value: "platform_rewrite", label: "根据平台重写同一章" },
] as const

export const PLATFORM_CONFIG: Record<string, {
  label: string
  icon: string
  description: string
  categories: string[]
}> = {
  tomato: {
    label: "番茄 / 七猫免费阅读",
    icon: "🍅",
    description: "强开局、强冲突、强反转、短章爽点、情绪刺激、结尾钩子",
    categories: [
      "玄幻", "都市", "科幻", "仙侠", "悬疑", "历史",
      "言情", "武侠", "轻小说", "游戏", "竞技", "同人",
      "军事", "现实"
    ],
  },
  qidian: {
    label: "起点 / QQ 阅读男频",
    icon: "📖",
    description: "世界观清晰、升级体系明确、长线伏笔、阶段性胜利、智斗和秩序感",
    categories: [
      "玄幻", "奇幻", "武侠", "仙侠", "都市", "现实",
      "历史", "军事", "游戏", "竞技", "科幻", "悬疑",
      "轻小说", "同人"
    ],
  },
  jjwxc: {
    label: "晋江 / 女频仙侠",
    icon: "🌸",
    description: "人物关系、情绪张力、双强拉扯、女主主体性、宿命感、感情递进",
    categories: [
      "仙侠", "古言", "现言", "奇幻", "科幻", "悬疑",
      "武侠", "历史", "都市", "轻小说"
    ],
  },
  short_drama: {
    label: "短剧 / IP 改编向",
    icon: "🎬",
    description: "名场面、视觉冲突、强反转、爆点台词、节奏密集、可剪辑爆点",
    categories: [
      "都市", "言情", "悬疑", "仙侠", "武侠", "科幻",
      "历史", "奇幻", "现实"
    ],
  },
  other: {
    label: "自定义平台",
    icon: "🌐",
    description: "自由设定读者偏好和创作约束",
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

// ── 新增补充类型 (Refactoring Additions) ──

export interface ApiCredential {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  is_default: boolean;
  created_at: string;
  status: string;
  api_key_last4?: string;
  last_tested_at?: string;
}

export interface ModelProfile {
  id: string;
  name: string;
  type: string;
  provider: string;
  is_default: boolean;
  api_credential_id?: string;
  model: string;
  health_status: string;
  is_active?: boolean;
  credential_name?: string;
  last_tested_at?: string;
}

export interface ModelAssignment {
  [key: string]: string | null;
}

export interface KnowledgeFile {
  id: number;
  project_id: string;
  filename: string;
  original_name: string;
  file_size: number;
  status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  error_message?: string;
  created_at: string;
}

export interface PlatformHookResult {
  score?: number;
  issues?: string[];
  suggestion?: string;
  rewrite_suggestion?: string;
  has_hook?: boolean;
  hook_type?: string;
  hook_strength?: string;
  hook_description?: string;
  rewritten_opening?: string;
}

export interface PlatformTitlesResult {
  titles: string[];
}

export interface PlatformBlurbResult {
  blurbs: string[];
}

export interface PlatformTagsResult {
  tags: any;
}

export interface PlatformDiagnosisResult {
  chapter_number: number;
  diagnosis: string;
  platform: string;
}

export interface MaterialEntity {
  id: string
  type: 'character' | 'world_rule' | 'plot_arc' | 'hook'
  title: string
  content: string
  tags: string[]
}

export interface DiagnosisReport {
  score: number
  is_compliant: boolean
  has_toxic_tropes: boolean
  issues: string[]
  missing_elements: string[]
  suggestion: string
}

export interface PromptMeta {
  key: string
  label: string
  group: string
  description: string
}

export interface PromptEntry extends PromptMeta {
  default_content: string
  custom_content: string | null
  is_overridden: boolean
}

export interface AnalyticsSummary {
  total_calls: number
  success_rate: number
  avg_latency_ms: number
  total_input_chars: number
  total_output_chars: number
  estimated_cost_cny: number
}

export interface ModelAnalytics {
  provider: string
  model: string
  count: number
  success_rate: number
  estimated_cost_cny: number
  input_chars: number
  output_chars: number
  avg_latency_ms: number
}

export interface PurposeAnalytics {
  purpose: string
  count: number
  success_rate: number
  estimated_cost_cny: number
  avg_latency_ms: number
}

export interface ProviderAnalytics {
  provider: string
  count: number
  success_rate: number
  estimated_cost_cny: number
  avg_latency_ms: number
}

export interface ErrorAnalytics {
  error_code: string
  count: number
  last_message: string
}

export interface DailyTrendAnalytics {
  date: string
  count: number
  success_rate: number
  estimated_cost_cny: number
  input_chars: number
  output_chars: number
}

export interface ProjectAnalytics {
  summary: AnalyticsSummary
  by_model: ModelAnalytics[]
  by_purpose: PurposeAnalytics[]
  by_provider: ProviderAnalytics[]
  errors: ErrorAnalytics[]
  daily_trend: DailyTrendAnalytics[]
}