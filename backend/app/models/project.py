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
    # 旧版 LLM 名称字段已废弃，请使用 /api/projects/{id}/model-assignment


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


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    type: str
    title: str
    filename: str
    content: str = ""
    source: str
    is_current: bool
    file_size: int
    created_at: str
    updated_at: str


class GenerationTaskResponse(BaseModel):
    id: str
    project_id: str
    type: str
    status: str
    input_snapshot: str = ""
    output_file_id: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    retryable: bool = False
    created_at: str
    updated_at: str
    finished_at: str | None = None
