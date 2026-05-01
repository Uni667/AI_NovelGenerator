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
  architecture_llm: string
  chapter_outline_llm: string
  prompt_draft_llm: string
  final_chapter_llm: string
  consistency_review_llm: string
  embedding_config: string
}

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
