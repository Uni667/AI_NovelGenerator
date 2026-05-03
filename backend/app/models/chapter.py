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
    status: str = "appeared"
    source: str = "user"
    first_appearance_chapter: Optional[int] = None
    updated_at: str


class CharacterProfileCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    status: str = "appeared"
    source: str = "user"
    first_appearance_chapter: Optional[int] = None


class CharacterProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    first_appearance_chapter: Optional[int] = None


class CharacterImportCandidate(BaseModel):
    candidate_id: str
    name: str
    normalized_name: str
    description: str = ""
    section: str = ""
    raw_text: str = ""
    entity_type: str = "character"
    confidence: float = 0.0
    decision: str = "review"
    reasons: List[str] = Field(default_factory=list)
    status: str = "planned"
    source: str = "ai"
    first_appearance_chapter: Optional[int] = None
    existing_character_id: Optional[int] = None
    matched_existing_name: str = ""
    aliases: List[str] = Field(default_factory=list)
    selected: bool = False


class CharacterImportSelection(BaseModel):
    selected_candidate_ids: List[str] = Field(default_factory=list)


# ── 角色关系图 ──

class CharacterRelationshipResponse(BaseModel):
    id: int
    project_id: str
    character_id_a: int
    character_id_b: int
    rel_type: str = ""
    description: str = ""
    strength: float = 0.5
    direction: str = "bidirectional"
    start_chapter: Optional[int] = None
    status: str = "active"
    updated_at: str


class CharacterRelationshipCreate(BaseModel):
    character_id_a: int
    character_id_b: int
    rel_type: str = ""
    description: str = ""
    strength: float = 0.5
    direction: str = "bidirectional"
    start_chapter: Optional[int] = None
    status: str = "active"


class CharacterRelationshipUpdate(BaseModel):
    rel_type: Optional[str] = None
    description: Optional[str] = None
    strength: Optional[float] = None
    direction: Optional[str] = None
    start_chapter: Optional[int] = None
    status: Optional[str] = None


# ── 冲突网 ──

class CharacterConflictResponse(BaseModel):
    id: int
    project_id: str
    title: str
    description: str = ""
    conflict_type: str = ""
    intensity: float = 0.5
    start_chapter: Optional[int] = None
    resolved_chapter: Optional[int] = None
    resolution: str = ""
    status: str = "active"
    updated_at: str
    participants: List[dict] = Field(default_factory=list)


class CharacterConflictCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    conflict_type: str = ""
    intensity: float = 0.5
    start_chapter: Optional[int] = None
    resolved_chapter: Optional[int] = None
    resolution: str = ""
    status: str = "active"
    participant_ids: List[int] = Field(default_factory=list)


class CharacterConflictUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    conflict_type: Optional[str] = None
    intensity: Optional[float] = None
    start_chapter: Optional[int] = None
    resolved_chapter: Optional[int] = None
    resolution: Optional[str] = None
    status: Optional[str] = None
    participant_ids: Optional[List[int]] = None


# ── 登场时间线 ──

class CharacterAppearanceResponse(BaseModel):
    id: int
    project_id: str
    character_id: int
    chapter_number: int
    appearance_type: str = "present"
    role_in_chapter: str = ""
    summary: str = ""
    updated_at: str


class CharacterAppearanceCreate(BaseModel):
    character_id: int
    chapter_number: int
    appearance_type: str = "present"
    role_in_chapter: str = ""
    summary: str = ""


class CharacterAppearanceUpdate(BaseModel):
    appearance_type: Optional[str] = None
    role_in_chapter: Optional[str] = None
    summary: Optional[str] = None
