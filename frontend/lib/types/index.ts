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
