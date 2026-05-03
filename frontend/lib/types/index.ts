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

export const APPEARANCE_TYPE_LABELS: Record<string, string> = {
  present: "登场", mentioned: "被提及", flashback: "闪回",
  implied: "暗示/伏笔", exit: "退场", return: "回归",
  transformation: "重大转变",
}
