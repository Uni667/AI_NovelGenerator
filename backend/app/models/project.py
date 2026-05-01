from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(default="未命名作品", max_length=100, description="项目名称")
    description: str = ""
    topic: str = ""
    genre: str = ""
    platform: str = Field(default="tomato", description="目标平台")
    category: str = Field(default="", description="平台内分类")
    num_chapters: int = Field(default=0, ge=0, description="章节总数")
    word_number: int = Field(default=3000, ge=500, le=50000, description="每章目标字数")
    user_guidance: str = ""
    language: str = "zh"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    filepath: str
    status: str
    created_at: str
    updated_at: str


class ConfigUpdate(BaseModel):
    topic: Optional[str] = None
    genre: Optional[str] = None
    num_chapters: Optional[int] = None
    word_number: Optional[int] = None
    user_guidance: Optional[str] = None
    language: Optional[str] = None
    platform: Optional[str] = None
    category: Optional[str] = None
    architecture_llm: Optional[str] = None
    chapter_outline_llm: Optional[str] = None
    prompt_draft_llm: Optional[str] = None
    final_chapter_llm: Optional[str] = None
    consistency_review_llm: Optional[str] = None
    embedding_config: Optional[str] = None


class ConfigResponse(BaseModel):
    project_id: str
    topic: str
    genre: str
    num_chapters: int
    word_number: int
    user_guidance: str
    language: str
    platform: str
    category: str
    architecture_llm: str
    chapter_outline_llm: str
    prompt_draft_llm: str
    final_chapter_llm: str
    consistency_review_llm: str
    embedding_config: str
