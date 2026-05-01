from pydantic import BaseModel, Field
from typing import Optional, List


class ChapterResponse(BaseModel):
    id: int
    project_id: str
    chapter_number: int
    chapter_title: str
    chapter_role: str
    chapter_purpose: str
    suspense_level: str
    foreshadowing: str
    plot_twist_level: str
    chapter_summary: str
    word_count: int
    status: str
    created_at: str
    updated_at: str


class ChapterContentResponse(BaseModel):
    chapter_number: int
    content: str
    meta: ChapterResponse


class ChapterUpdate(BaseModel):
    chapter_title: Optional[str] = None
    content: Optional[str] = None


class KnowledgeFileResponse(BaseModel):
    id: int
    project_id: str
    filename: str
    file_size: int
    imported: int
    created_at: str


class CharacterProfileResponse(BaseModel):
    id: int
    project_id: str
    name: str
    description: str
    updated_at: str


class CharacterProfileCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""


class CharacterProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
