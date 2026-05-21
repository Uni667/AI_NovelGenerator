from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: str = ""
    topic: str = ""
    genre: str = ""
    platform: str = Field(default="tomato", description="Target platform")
    category: str = Field(default="", description="Platform category")
    num_chapters: int = Field(default=0, ge=0, description="Chapter count")
    word_number: int = Field(default=3000, ge=500, le=50000, description="Target words per chapter")
    user_guidance: str = ""
    language: str = "zh"
    target_reader: str = ""
    reader_direction: str = ""
    trend_key: str = ""
    custom_trend: str = ""
    trend_translation: str = ""
    forbidden: str = ""
    style_requirement: str = ""


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
    target_reader: Optional[str] = None
    reader_direction: Optional[str] = None
    trend_key: Optional[str] = None
    custom_trend: Optional[str] = None
    trend_translation: Optional[str] = None
    forbidden: Optional[str] = None
    style_requirement: Optional[str] = None


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
    target_reader: str = ""
    reader_direction: str = ""
    trend_key: str = ""
    custom_trend: str = ""
    trend_translation: str = ""
    forbidden: str = ""
    style_requirement: str = ""


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
