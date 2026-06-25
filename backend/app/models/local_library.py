from typing import List, Optional
from pydantic import BaseModel, Field


class LocalLibraryConfigBase(BaseModel):
    source_dir: str = Field(default="", description="小说原文文件夹路径")
    essence_dir: str = Field(default="", description="精华输出文件夹路径")
    cache_dir: str = Field(default="", description="缓存文件夹路径")
    log_dir: str = Field(default="", description="日志文件夹路径")
    allow_local_file_access: bool = Field(default=False, description="是否允许访问本地文件")
    max_file_mb: int = Field(default=500, description="单文件大小上限(MB)")
    allowed_extensions: List[str] = Field(default_factory=lambda: [".txt", ".md", ".epub", ".docx"], description="允许的扩展名")
    watcher_enabled: bool = Field(default=False, description="是否启用文件夹监听")


class LocalLibraryConfigUpdate(BaseModel):
    source_dir: Optional[str] = None
    essence_dir: Optional[str] = None
    cache_dir: Optional[str] = None
    log_dir: Optional[str] = None
    allow_local_file_access: Optional[bool] = None
    max_file_mb: Optional[int] = None
    allowed_extensions: Optional[List[str]] = None
    watcher_enabled: Optional[bool] = None


class LocalLibraryConfigResponse(LocalLibraryConfigBase):
    id: int
    created_at: str
    updated_at: str


class LocalReferenceBookResponse(BaseModel):
    id: str
    title: str
    author_label: str = "unknown"
    category: str = ""
    tags: List[str] = Field(default_factory=list)
    source_file_path: str
    source_file_name: str
    source_file_ext: str
    source_file_hash: str
    source_file_size: int
    source_file_mtime: str
    source_encoding: str = "utf-8"
    copyright_status: str = "unknown"
    parse_status: str = "new"
    absorb_status: str = "not_started"
    similarity_status: str = "not_built"
    essence_dir_path: str = ""
    manifest_path: str = ""
    total_chapters: int = 0
    total_volumes: int = 0
    total_words: int = 0
    parse_confidence: float = 0.0
    last_scanned_at: Optional[str] = None
    last_parsed_at: Optional[str] = None
    last_absorbed_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class LocalReferenceVolumeResponse(BaseModel):
    id: str
    book_id: str
    volume_index: int
    title: str
    start_chapter_index: int
    end_chapter_index: int
    summary_path: Optional[str] = None
    analysis_path: Optional[str] = None
    word_count: int = 0


class LocalReferenceChapterResponse(BaseModel):
    id: str
    book_id: str
    volume_id: Optional[str] = None
    chapter_index: int
    title: str
    source_start_offset: int
    source_end_offset: int
    word_count: int
    summary_path: Optional[str] = None
    analysis_path: Optional[str] = None
    scene_patterns_path: Optional[str] = None
    parse_confidence: float = 1.0


class LocalReferenceChapterUpdate(BaseModel):
    title: Optional[str] = None
    chapter_index: Optional[int] = None
    needs_review: Optional[bool] = None


class ProjectReferenceBindingRequest(BaseModel):
    book_id: str
    enabled: bool = True
    weight: float = 1.0
    use_style_bible: bool = True
    use_scene_patterns: bool = True
    use_pacing_rules: bool = True
    use_character_arcs: bool = True
    use_anti_copy_guard: bool = True
    max_rules_per_generation: int = 5


class ProjectReferenceBindingResponse(BaseModel):
    id: str
    project_id: str
    book_id: str
    enabled: bool
    weight: float
    use_style_bible: bool
    use_scene_patterns: bool
    use_pacing_rules: bool
    use_character_arcs: bool
    use_anti_copy_guard: bool
    max_rules_per_generation: int
    created_at: str
    updated_at: str


class ReferenceAbsorptionTaskResponse(BaseModel):
    id: str
    task_id: str
    book_id: str
    task_type: str
    status: str
    progress_current: int
    progress_total: int
    current_step: str
    error_message: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    created_at: str


class ScanReportResponse(BaseModel):
    source_dir: str
    total_files: int
    new_books: int
    changed_books: int
    deleted_books: int
    unchanged_books: int
    errors: List[str] = Field(default_factory=list)
