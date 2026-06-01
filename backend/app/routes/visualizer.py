import os
import json
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.services.sync_service import sync_db_to_txt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["可视化与互动"])

# Prompt template for parsing characters, scenes, and events from a chapter
CHAPTER_PARSING_PROMPT = """你是网文小说设定与剧情可视化专家。请仔细阅读以下小说章节内容，解析出人物、场景和关键剧情分镜事件，并生成用于AI绘图（如Stable Diffusion/Midjourney）的英文提示词。

## 章节内容：
{content}

## 输出格式要求：
请严格返回一个 JSON 对象，不要包含 markdown 标记（如 ```json）或任何其他解释文字。结构必须完全符合以下 JSON 格式：
{{
  "characters": [
    {{
      "name": "人物名称（必须是书中出现的中文名字，如：林逸）",
      "aliases": ["别名1", "别名2"],
      "roleType": "主角" 或 "女主" 或 "配角" 或 "反派" 或 "NPC" 或 "未知",
      "gender": "男" 或 "女" 或 "不明",
      "age": "年龄，如：18岁、少年、中年",
      "faction": "所属势力/门派/阵营，如：玄天宗",
      "identity": "身份，如：掌门弟子、流浪汉、僵尸王",
      "personalityTags": ["性格标签1", "性格标签2"],
      "appearance": "外貌衣着发型详细描述，50字以内",
      "abilities": ["技能/功法1", "技能/功法2"],
      "currentStatus": "本章结束时该角色的位置/处境/状态，30字以内",
      "relationships": [
        {{
          "targetCharacterName": "目标角色名称",
          "relationType": "伙伴" 或 "敌对" 或 "暧昧" 或 "师徒" 或 "亲人" 或 "合作" 或 "未知",
          "description": "关系描述，如：深仇大恨、暗中倾慕"
        }}
      ],
      "avatarPrompt": "A detailed English prompt for drawing a cute chibi anime avatar of this character, e.g., 'Chibi anime boy, black hair, wearing daoist robe, holding a wooden sword, white background, masterpiece, 8k'"
    }}
  ],
  "scenes": [
    {{
      "name": "地点/场景名称，如：落阳镇棺庙",
      "type": "类型，如：古墓、密室、森林、客栈",
      "description": "环境特征详细描述，50字以内",
      "atmosphere": "氛围，如：阴森、古老、祥和、诡异",
      "imagePrompt": "A detailed English prompt for drawing this location scene, e.g., 'Eerie ancient tomb interior, glowing emerald lamps, stone coffins, dust motes, fantasy digital art, cinematic lighting'"
    }}
  ],
  "events": [
    {{
      "title": "事件标题，如：青铜棺开棺",
      "summary": "事件具体发生内容，70字以内",
      "sceneName": "发生的地点/场景名称",
      "involvedCharacterNames": ["参与角色A", "参与角色B"],
      "mood": "情绪氛围，如：紧张、热血、悲伤、惊悚",
      "consequences": "该事件对后续剧情产生的直接后果，50字以内",
      "storyboardPrompt": "A detailed English storyboard prompt for this scene panel, e.g., 'A close-up shot of a golden coffin cracking open with green smoke leaking out, hand rising, dark atmospheric tomb, anime style storyboard'"
    }}
  ]
}}
"""

def _check_project(project_id: str, request: Request) -> dict:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project

def _get_visualizer_data_path(project_filepath: str) -> str:
    return os.path.join(project_filepath, "visualizer_data.json")

def _load_raw_visualizer_data(project_filepath: str) -> dict:
    path = _get_visualizer_data_path(project_filepath)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "characters" not in data: data["characters"] = []
                if "scenes" not in data: data["scenes"] = []
                if "events" not in data: data["events"] = []
                if "schemaVersion" not in data: data["schemaVersion"] = 1
                return data
        except Exception as e:
            logger.error(f"Failed to load raw visualizer data: {e}")
            
    return {"schemaVersion": 2, "characters": [], "scenes": [], "events": []}

def _save_visualizer_data(project_filepath: str, data: dict):
    path = _get_visualizer_data_path(project_filepath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _migrate_and_sync_visualizer_data(project_filepath: str, project_id: str) -> dict:
    data = _load_raw_visualizer_data(project_filepath)
    version = data.get("schemaVersion", 1)
    
    # Query database characters
    db_chars = []
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM character_profile WHERE project_id = ?", (project_id,)).fetchall()
            db_chars = [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to query DB characters for sync: {e}")
        
    db_char_by_name = {c["name"].lower().strip(): c for c in db_chars}
    db_char_by_id = {c["id"]: c for c in db_chars}
    
    if version < 2:
        logger.info(f"Migrating project {project_id} visualizer data from schemaVersion {version} to 2 (UUID character IDs)")
        name_to_uuid = {}
        # 1. Assign UUIDs
        for char in data.get("characters", []):
            old_id = char.get("id")
            # Check if it is already a UUID
            is_uuid = False
            if old_id:
                try:
                    uuid.UUID(old_id)
                    is_uuid = True
                except ValueError:
                    pass
            c_uuid = old_id if is_uuid else str(uuid.uuid4())
            name_to_uuid[old_id] = c_uuid
            char["id"] = c_uuid
            
            # Link dbCharacterId
            name_lower = char.get("name", "").strip().lower()
            if "dbCharacterId" not in char and name_lower in db_char_by_name:
                char["dbCharacterId"] = db_char_by_name[name_lower]["id"]
                
        # 2. Update relationships
        for char in data.get("characters", []):
            rels = char.get("relationships", [])
            for r in rels:
                src = r.get("sourceCharacterId")
                tgt = r.get("targetCharacterId")
                r["sourceCharacterId"] = name_to_uuid.get(src, src)
                r["targetCharacterId"] = name_to_uuid.get(tgt, tgt)
                
        # 3. Update scene characterIds
        for scene in data.get("scenes", []):
            c_ids = scene.get("characterIds", [])
            scene["characterIds"] = [name_to_uuid.get(cid, cid) for cid in c_ids]
            
        # 4. Update event characterIds
        for event in data.get("events", []):
            c_ids = event.get("characterIds", [])
            event["characterIds"] = [name_to_uuid.get(cid, cid) for cid in c_ids]
            
        data["schemaVersion"] = 2
        _save_visualizer_data(project_filepath, data)
        
    # Sync visualizer characters with database (CharactersTab) updates
    has_changes = False
    for char in data.get("characters", []):
        db_id = char.get("dbCharacterId")
        db_char = None
        if db_id and db_id in db_char_by_id:
            db_char = db_char_by_id[db_id]
        else:
            name_lower = char.get("name", "").strip().lower()
            if name_lower in db_char_by_name:
                db_char = db_char_by_name[name_lower]
                char["dbCharacterId"] = db_char["id"]
                has_changes = True
                
        if db_char:
            manual_fields = char.get("manualFields", [])
            if "name" not in manual_fields and char["name"] != db_char["name"]:
                char["name"] = db_char["name"]
                has_changes = True
            if "description" not in manual_fields and char.get("description", "") != db_char.get("description", ""):
                char["description"] = db_char["description"] or ""
                has_changes = True
        elif db_id:
            # db character was deleted
            char["dbCharacterId"] = None
            has_changes = True
            
    if has_changes:
        _save_visualizer_data(project_filepath, data)
        
    return data

def _load_visualizer_data(project_filepath: str, project_id: str | None = None) -> dict:
    if project_id:
        return _migrate_and_sync_visualizer_data(project_filepath, project_id)
    return _load_raw_visualizer_data(project_filepath)

def _raise_structured_error(code: str, message: str, stage: str, retryable: bool = True, details: str | None = None, raw_excerpt: str | None = None):
    detail = {
        "code": code,
        "message": message,
        "details": {
            "stage": stage,
            "retryable": retryable,
            "rawExcerpt": raw_excerpt,
            "details": details
        }
    }
    raise HTTPException(status_code=400, detail=detail)

@router.get("/api/v1/projects/{project_id}/visualizer/data")
def get_visualizer_data(project_id: str, request: Request):
    """获取小说可视化全量数据，包括人物图鉴、场景画廊、剧情分镜及关系图"""
    project = _check_project(project_id, request)
    return _load_visualizer_data(project["filepath"], project_id)

@router.post("/api/v1/projects/{project_id}/visualizer/analyze-chapters")
def analyze_chapters(project_id: str, request: Request, chapter_number: int | None = None):
    """AI 自动分析小说章节文本，提取人物属性、场景画廊与分镜时间线数据"""
    project = _check_project(project_id, request)
    user_id = get_current_user(request)
    
    # 1. Fetch chapters to parse
    with get_db() as conn:
        if chapter_number is not None:
            rows = conn.execute(
                "SELECT chapter_number, chapter_title, content FROM chapter WHERE project_id = ? AND chapter_number = ?",
                (project_id, chapter_number)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT chapter_number, chapter_title, content FROM chapter WHERE project_id = ? AND content IS NOT NULL AND content != '' ORDER BY chapter_number",
                (project_id,)
            ).fetchall()
            
    chapters_to_parse = [dict(r) for r in rows if r["content"] and r["content"].strip()]
    if not chapters_to_parse:
        _raise_structured_error("EMPTY_CHAPTER", "未找到有文字内容的章节，请先在章节工作台中编写或生成章节。", "validate", False)
        
    # 2. Initialize LLM Adapter
    from backend.app.services.model_runtime import _build_chat_adapter
    from backend.app.services.config_resolver import get_runtime_config, ConfigError
    
    try:
        runtime_cfg = get_runtime_config(user_id, "character", project_id)
    except ConfigError as e:
        _raise_structured_error("CONFIG_ERROR", f"配置加载失败: {str(e)}", "request", False)
        
    try:
        llm = _build_chat_adapter(runtime_cfg, runtime_cfg.temperature, runtime_cfg.max_tokens)
    except Exception as e:
        _raise_structured_error("API_INIT_ERROR", f"模型初始化失败: {str(e)}", "request", False)
    
    # Load existing data
    data = _load_visualizer_data(project["filepath"], project_id)
    
    parsed_chapters = []
    new_char_count = 0
    new_scene_count = 0
    new_event_count = 0
    
    for ch in chapters_to_parse:
        ch_num = ch["chapter_number"]
        ch_str = str(ch_num)
        content_snippet = ch["content"][:6000] # Stay within context limits
        
        prompt = CHAPTER_PARSING_PROMPT.format(content=content_snippet)
        
        # Invoke LLM
        try:
            response = llm.invoke(prompt)
        except Exception as e:
            _raise_structured_error("API_ERROR", f"AI 请求失败: {str(e)}", "request", True)
            
        if not response or not response.strip():
            _raise_structured_error("EMPTY_RESPONSE", f"AI 章节 {ch_num} 返回为空", "response", True)
            
        # Find JSON block boundaries
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            _raise_structured_error("PARSE_ERROR", f"AI 返回格式错误，非有效 JSON 结构", "parse", True, raw_excerpt=response[:300])
            
        try:
            parsed_data = json.loads(response[json_start:json_end])
        except Exception as e:
            _raise_structured_error("PARSE_ERROR", f"JSON 反序列化失败: {str(e)}", "parse", True, raw_excerpt=response[json_start:json_start+300])
            
        # Validate schema structure briefly
        if not isinstance(parsed_data, dict) or "characters" not in parsed_data or "scenes" not in parsed_data or "events" not in parsed_data:
            _raise_structured_error("VALIDATE_ERROR", "AI 返回 JSON 的 schema 校验失败，缺少必要的一级字段", "validate", True, raw_excerpt=response[json_start:json_start+300])
            
        # Delete existing events for this chapter to avoid duplicates on re-parse
        data["events"] = [e for e in data["events"] if e.get("chapterId") != ch_str]
        
        # --- A. Process Characters ---
        for c_ext in parsed_data.get("characters", []):
            name = str(c_ext.get("name", "")).strip()
            if not name:
                continue
            
            # Character matching ranking: Medium (name match), Weak (alias match), else New
            match_char = None
            match_type = None
            
            # Exact name match
            for c in data["characters"]:
                if c["name"].lower() == name.lower():
                    match_char = c
                    match_type = 'medium'
                    break
            
            # Alias match
            if not match_char:
                aliases = [a.lower().strip() for a in c_ext.get("aliases", []) if a]
                for c in data["characters"]:
                    c_name_lower = c["name"].lower().strip()
                    c_aliases_lower = [a.lower().strip() for a in c.get("aliases", [])]
                    
                    if name.lower() in c_aliases_lower:
                        match_char = c
                        match_type = 'weak'
                        break
                    if any(a in aliases for a in [c_name_lower] + c_aliases_lower):
                        match_char = c
                        match_type = 'weak'
                        break
            
            # Extract roleType and validate options
            role_type = c_ext.get("roleType", "未知")
            if role_type not in ('主角', '女主', '配角', '反派', 'NPC', '未知'):
                role_type = "未知"
            
            # Format relationships temporarily (using names; we map names to UUIDs later)
            rels = []
            for r_ext in c_ext.get("relationships", []):
                target_name = str(r_ext.get("targetCharacterName", "")).strip()
                rel_type = r_ext.get("relationType", "未知")
                if rel_type not in ('伙伴', '敌对', '暧昧', '师徒', '亲人', '合作', '未知'):
                    rel_type = "未知"
                if target_name:
                    rels.append({
                        "sourceCharacterId": name,
                        "targetCharacterId": target_name,
                        "relationType": rel_type,
                        "description": r_ext.get("description", "")
                    })

            # Update existing or create new
            if match_char and match_type == 'medium':
                char = match_char
                manual_fields = char.get("manualFields", [])
                
                if "roleType" not in manual_fields:
                    char["roleType"] = role_type
                if "gender" not in manual_fields and c_ext.get("gender"):
                    char["gender"] = c_ext.get("gender")
                if "age" not in manual_fields and c_ext.get("age"):
                    char["age"] = c_ext.get("age")
                if "faction" not in manual_fields and c_ext.get("faction"):
                    char["faction"] = c_ext.get("faction")
                if "identity" not in manual_fields and c_ext.get("identity"):
                    char["identity"] = c_ext.get("identity")
                if "appearance" not in manual_fields and c_ext.get("appearance"):
                    char["appearance"] = c_ext.get("appearance")
                if "currentStatus" not in manual_fields and c_ext.get("currentStatus"):
                    char["currentStatus"] = c_ext.get("currentStatus")
                    
                # Merge lists
                if "aliases" not in manual_fields:
                    char["aliases"] = list(set((char.get("aliases") or []) + c_ext.get("aliases", [])))
                char["personalityTags"] = list(set((char.get("personalityTags") or []) + c_ext.get("personalityTags", [])))
                char["abilities"] = list(set((char.get("abilities") or []) + c_ext.get("abilities", [])))
                
                # Update timeline
                if ch_str not in char["relatedChapterIds"]:
                    char["relatedChapterIds"].append(ch_str)
                char["relatedChapterIds"].sort(key=int)
                char["lastChapterId"] = ch_str
                
                # Merge relationships
                existing_rels = char.get("relationships") or []
                for r_new in rels:
                    r_idx = -1
                    for r_e_idx, r_e in enumerate(existing_rels):
                        if r_e["targetCharacterId"].lower() == r_new["targetCharacterId"].lower():
                            r_idx = r_e_idx
                            break
                    if r_idx >= 0:
                        existing_rels[r_idx] = r_new
                    else:
                        existing_rels.append(r_new)
                char["relationships"] = existing_rels
                
                # Prompt updates
                if c_ext.get("avatarPrompt") and "avatarPrompt" not in manual_fields:
                    char["avatarPrompt"] = c_ext.get("avatarPrompt")
                    if char.get("imageStatus", "none") == "none":
                        char["imageStatus"] = "prompt_ready"
            else:
                # Weak match (creates new, flags unconfirmed) or New character
                c_uuid = str(uuid.uuid4())
                new_char = {
                    "id": c_uuid,
                    "projectId": project_id,
                    "name": name,
                    "aliases": c_ext.get("aliases", []),
                    "roleType": role_type,
                    "gender": c_ext.get("gender", "不明"),
                    "age": c_ext.get("age", "不明"),
                    "faction": c_ext.get("faction", "未知"),
                    "identity": c_ext.get("identity", "普通角色"),
                    "personalityTags": c_ext.get("personalityTags", []),
                    "appearance": c_ext.get("appearance", ""),
                    "abilities": c_ext.get("abilities", []),
                    "currentStatus": c_ext.get("currentStatus", "初登场"),
                    "firstChapterId": ch_str,
                    "lastChapterId": ch_str,
                    "relatedChapterIds": [ch_str],
                    "relationships": rels,
                    "avatarUrl": "",
                    "chibiAvatarUrl": "",
                    "avatarPrompt": c_ext.get("avatarPrompt", ""),
                    "imageStatus": "prompt_ready" if c_ext.get("avatarPrompt") else "none"
                }
                
                if match_char and match_type == 'weak':
                    new_char["isUnconfirmed"] = True
                    new_char["pendingMergeWithId"] = match_char["id"]
                
                data["characters"].append(new_char)
                new_char_count += 1
                
        # --- B. Process Scenes ---
        for s_ext in parsed_data.get("scenes", []):
            s_name = str(s_ext.get("name", "")).strip()
            if not s_name:
                continue
            
            scene_idx = -1
            for idx, s in enumerate(data["scenes"]):
                if s["name"].lower() == s_name.lower():
                    scene_idx = idx
                    break
            
            # Check which characters are active in this chapter and belong to this scene
            present_char_names = []
            for c_ext in parsed_data.get("characters", []):
                c_name = str(c_ext.get("name", "")).strip()
                if c_name:
                    present_char_names.append(c_name)

            if scene_idx >= 0:
                scene = data["scenes"][scene_idx]
                scene["type"] = s_ext.get("type", scene.get("type", ""))
                scene["description"] = s_ext.get("description", scene.get("description", ""))
                scene["atmosphere"] = s_ext.get("atmosphere", scene.get("atmosphere", ""))
                if s_ext.get("imagePrompt"):
                    scene["imagePrompt"] = s_ext.get("imagePrompt")
                
                if ch_str not in scene["relatedChapterIds"]:
                    scene["relatedChapterIds"].append(ch_str)
                scene["relatedChapterIds"].sort(key=int)
                
                scene["characterIds"] = list(set((scene.get("characterIds") or []) + present_char_names))
            else:
                new_scene = {
                    "id": str(uuid.uuid4()),
                    "projectId": project_id,
                    "name": s_name,
                    "type": s_ext.get("type", "普通场景"),
                    "description": s_ext.get("description", ""),
                    "atmosphere": s_ext.get("atmosphere", "普通氛围"),
                    "relatedChapterIds": [ch_str],
                    "characterIds": present_char_names,
                    "imageUrl": "",
                    "imagePrompt": s_ext.get("imagePrompt", "")
                }
                data["scenes"].append(new_scene)
                new_scene_count += 1
                
        # --- C. Process Events (Storyboards) ---
        for idx, e_ext in enumerate(parsed_data.get("events", [])):
            event_title = str(e_ext.get("title", "")).strip()
            if not event_title:
                continue
            
            involved_chars = [str(n).strip() for n in e_ext.get("involvedCharacterNames", []) if n]
            scene_name = str(e_ext.get("sceneName", "")).strip()
            
            new_event = {
                "id": f"{ch_str}_{idx}_{uuid.uuid4().hex[:4]}",
                "projectId": project_id,
                "chapterId": ch_str,
                "title": event_title,
                "summary": e_ext.get("summary", ""),
                "sceneId": scene_name if scene_name else None,
                "characterIds": involved_chars,
                "mood": e_ext.get("mood", "普通情绪"),
                "consequences": e_ext.get("consequences", ""),
                "storyboardPrompt": e_ext.get("storyboardPrompt", ""),
                "imageUrl": ""
            }
            data["events"].append(new_event)
            new_event_count += 1
            
        parsed_chapters.append(ch_num)

    # Resolve character names to UUIDs in relationships, events, and scenes
    name_to_uuid = {c["name"].lower().strip(): c["id"] for c in data["characters"]}
    for char in data["characters"]:
        resolved_rels = []
        for rel in char.get("relationships", []):
            src_uuid = name_to_uuid.get(rel["sourceCharacterId"].lower().strip(), rel["sourceCharacterId"])
            tgt_uuid = name_to_uuid.get(rel["targetCharacterId"].lower().strip(), rel["targetCharacterId"])
            resolved_rels.append({
                "sourceCharacterId": src_uuid,
                "targetCharacterId": tgt_uuid,
                "relationType": rel["relationType"],
                "description": rel["description"]
            })
        char["relationships"] = resolved_rels
        
    for scene in data["scenes"]:
        scene["characterIds"] = [name_to_uuid.get(cid.lower().strip(), cid) for cid in scene.get("characterIds", [])]
        
    for event in data["events"]:
        event["characterIds"] = [name_to_uuid.get(cid.lower().strip(), cid) for cid in event.get("characterIds", [])]
        # Resolve scene name to scene ID
        scene_name = event.get("sceneId")
        if scene_name:
            for s in data["scenes"]:
                if s["name"].lower().strip() == scene_name.lower().strip():
                    event["sceneId"] = s["id"]
                    break

    # Synchronize confirmed visualizer characters with database character_profile
    try:
        now_str = datetime.now().isoformat()
        with get_db() as conn:
            for char in data.get("characters", []):
                if char.get("isUnconfirmed"):
                    continue
                db_id = char.get("dbCharacterId")
                name = char["name"]
                desc = char.get("identity", "")
                if char.get("appearance"):
                    desc += f" - {char.get('appearance')}"
                first_app = None
                if char.get("firstChapterId"):
                    try:
                        first_app = int(char["firstChapterId"])
                    except ValueError:
                        pass
                
                existing = None
                if db_id:
                    existing = conn.execute("SELECT id FROM character_profile WHERE id = ?", (db_id,)).fetchone()
                else:
                    existing = conn.execute("SELECT id FROM character_profile WHERE project_id = ? AND name = ?", (project_id, name)).fetchone()
                
                if existing:
                    char["dbCharacterId"] = existing["id"]
                else:
                    cursor = conn.execute(
                        """INSERT INTO character_profile 
                           (project_id, name, description, status, source, first_appearance_chapter, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (project_id, name, desc[:1000], "appeared", "ai", first_app, now_str)
                    )
                    char["dbCharacterId"] = cursor.lastrowid
            conn.commit()
    except Exception as db_err:
        logger.error(f"Failed to sync visualizer characters to SQLite DB: {db_err}")

    # Save back aggregated visualizer data
    if parsed_chapters:
        try:
            _save_visualizer_data(project["filepath"], data)
            sync_db_to_txt(project_id)
        except Exception as e:
            _raise_structured_error("SAVE_ERROR", f"数据保存失败: {str(e)}", "save", True)
        
    return {
        "parsed_chapters": parsed_chapters,
        "new_characters_count": new_char_count,
        "new_scenes_count": new_scene_count,
        "new_events_count": new_event_count
    }

class ImagePromptRequest(BaseModel):
    id: str
    type: str

@router.post("/api/v1/projects/{project_id}/visualizer/generate-prompt")
def generate_asset_prompt(project_id: str, request: Request, payload: ImagePromptRequest):
    """按需为人物、场景或分镜生成绘图提示词"""
    project = _check_project(project_id, request)
    user_id = get_current_user(request)
    
    data = _load_visualizer_data(project["filepath"], project_id)
    asset_id = payload.id
    asset_type = payload.type
    
    # Initialize LLM Adapter
    from backend.app.services.model_runtime import _build_chat_adapter
    from backend.app.services.config_resolver import get_runtime_config, ConfigError
    try:
        runtime_cfg = get_runtime_config(user_id, "character", project_id)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    llm = _build_chat_adapter(runtime_cfg, runtime_cfg.temperature, runtime_cfg.max_tokens)
    
    prompt_result = ""
    
    if asset_type == "character":
        char_found = None
        for char in data["characters"]:
            if char["id"] == asset_id:
                char_found = char
                break
        if not char_found:
            raise HTTPException(status_code=404, detail="人物未找到")
            
        prompt = f"""请根据以下人物设定，生成一段用于 AI 绘图生成该角色头像的英文提示词。要求生成萌系、精细可爱的二次元/Q版风格。
人物名称: {char_found['name']}
身份职业: {char_found.get('identity')}
外貌衣着: {char_found.get('appearance')}
性格标签: {', '.join(char_found.get('personalityTags', []))}
所属势力: {char_found.get('faction')}

输出要求: 直接输出英文提示词（Prompt），包含角色外观、表情、画风设定（如 chibi anime style, cute, detailed, avatar, white background）。不要有任何解释性文字或 Markdown 标记。"""
        try:
            prompt_result = llm.invoke(prompt).strip()
            char_found["avatarPrompt"] = prompt_result
            char_found["imageStatus"] = "prompt_ready"
            _save_visualizer_data(project["filepath"], data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"生成提示词失败: {e}")
            
    elif asset_type == "scene":
        scene_found = None
        for scene in data["scenes"]:
            if scene["id"] == asset_id:
                scene_found = scene
                break
        if not scene_found:
            raise HTTPException(status_code=404, detail="场景未找到")
            
        prompt = f"""请根据以下场景设定，生成一段用于 AI 绘图生成该场景全景图的英文提示词。风格偏向幻想插画/半写实概念设计风格。
场景名称: {scene_found['name']}
类型标签: {scene_found.get('type')}
场景描述: {scene_found.get('description')}
场景氛围: {scene_found.get('atmosphere')}

输出要求: 直接输出英文提示词（Prompt），包含场景细节、光影、画面质感和风格设定（如 concept art, fantasy environment, volumetric lighting, detailed）。不要有任何解释性文字或 Markdown 标记。"""
        try:
            prompt_result = llm.invoke(prompt).strip()
            scene_found["imagePrompt"] = prompt_result
            _save_visualizer_data(project["filepath"], data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"生成提示词失败: {e}")
            
    elif asset_type == "event":
        event_found = None
        for event in data["events"]:
            if event["id"] == asset_id:
                event_found = event
                break
        if not event_found:
            raise HTTPException(status_code=404, detail="分镜事件未找到")
            
        prompt = f"""请根据以下剧情事件，生成一段用于 AI 绘图生成漫画/小说分镜插画的英文提示词。要求偏向动漫插图、镜头感强的画面。
事件标题: {event_found['title']}
事件发生场景: {event_found.get('sceneId')}
事件内容描述: {event_found.get('summary')}
情绪氛围: {event_found.get('mood')}
参与角色: {', '.join(event_found.get('characterIds', []))}

输出要求: 直接输出英文提示词（Prompt），包含构图视角、光影、镜头聚焦、动作神态和风格设定（如 dramatic shot, anime key visual, epic storyboard panel, action scene）。不要有任何解释性文字或 Markdown 标记。"""
        try:
            prompt_result = llm.invoke(prompt).strip()
            event_found["storyboardPrompt"] = prompt_result
            _save_visualizer_data(project["filepath"], data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"生成提示词失败: {e}")
            
    else:
        raise HTTPException(status_code=400, detail="未知的资源类型")
        
    return {"prompt": prompt_result}

@router.put("/api/v1/projects/{project_id}/visualizer/characters/{char_id}")
def update_visualizer_character(project_id: str, char_id: str, request: Request, payload: dict):
    """更新人物图鉴属性"""
    project = _check_project(project_id, request)
    data = _load_visualizer_data(project["filepath"], project_id)
    
    char_found = None
    for char in data["characters"]:
        if char["id"] == char_id:
            char_found = char
            break
            
    if not char_found:
        raise HTTPException(status_code=404, detail="人物未找到")
        
    # Maintain manual edited flags to prevent AI overwriting
    manual_fields = char_found.get("manualFields", [])
    
    # Apply updates
    fields = ("name", "roleType", "gender", "age", "faction", "identity", "appearance", "currentStatus", "avatarUrl", "avatarPrompt", "imageStatus")
    for field in fields:
        if field in payload:
            char_found[field] = payload[field]
            if field not in manual_fields:
                manual_fields.append(field)
                
    if "aliases" in payload:
        char_found["aliases"] = payload["aliases"]
        if "aliases" not in manual_fields:
            manual_fields.append("aliases")
            
    if "personalityTags" in payload:
        char_found["personalityTags"] = payload["personalityTags"]
    if "abilities" in payload:
        char_found["abilities"] = payload["abilities"]
    if "relationships" in payload:
        char_found["relationships"] = payload["relationships"]
        if "relationships" not in manual_fields:
            manual_fields.append("relationships")
        
    char_found["manualFields"] = manual_fields
    char_found["manual"] = True
    
    # Synchronize manual edit back to SQLite character_profile
    db_id = char_found.get("dbCharacterId")
    if db_id:
        try:
            desc = char_found.get("identity", "")
            if char_found.get("appearance"):
                desc += f" - {char_found.get('appearance')}"
            with get_db() as conn:
                conn.execute(
                    "UPDATE character_profile SET name = ?, description = ?, updated_at = ? WHERE id = ?",
                    (char_found["name"], desc[:1000], datetime.now().isoformat(), db_id)
                )
                conn.commit()
        except Exception as db_err:
            logger.error(f"Failed to sync manual edit back to SQLite DB character: {db_err}")
    
    _save_visualizer_data(project["filepath"], data)
    return char_found

@router.get("/api/v1/projects/{project_id}/visualizer/characters/{char_id}")
def get_visualizer_character(project_id: str, char_id: str, request: Request):
    """获取指定角色详情，并自动同步 SQLite 最新设定数据"""
    project = _check_project(project_id, request)
    data = _load_visualizer_data(project["filepath"], project_id)
    
    for char in data.get("characters", []):
        if char["id"] == char_id:
            return char
            
    raise HTTPException(status_code=404, detail="人物未找到")

@router.post("/api/v1/projects/{project_id}/visualizer/characters/{char_id}/generate-avatar")
def generate_character_avatar(project_id: str, char_id: str, request: Request):
    """按需生成角色的 AI 头像。在 ENABLE_VISUALIZER_IMAGE_GENERATION 启用时生成 SVG 矢量卡通头像"""
    enable_gen = os.getenv("ENABLE_VISUALIZER_IMAGE_GENERATION", "false").lower() == "true"
    if not enable_gen:
        raise HTTPException(status_code=403, detail="头像自动生成功能未启用")
        
    project = _check_project(project_id, request)
    data = _load_visualizer_data(project["filepath"], project_id)
    
    char_found = None
    for char in data.get("characters", []):
        if char["id"] == char_id:
            char_found = char
            break
            
    if not char_found:
        raise HTTPException(status_code=404, detail="人物未找到")
        
    # Generate a beautiful stylized SVG vector avatar
    assets_dir = os.path.join(project["filepath"], "visualizer_assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    avatar_filename = f"{char_id}.svg"
    avatar_path = os.path.join(assets_dir, avatar_filename)
    
    name = char_found["name"]
    initial = name[0] if name else "C"
    
    # Pick a cool gradient based on roleType
    gradient_colors = {
        "主角": ("#8b5cf6", "#4f46e5"), # purple to indigo
        "女主": ("#ec4899", "#d946ef"), # pink to fuchsia
        "反派": ("#ef4444", "#991b1b"), # red to dark red
        "配角": ("#3b82f6", "#0ea5e9"), # blue to sky blue
    }
    col_start, col_end = gradient_colors.get(char_found.get("roleType", "未知"), ("#6b7280", "#374151"))
    
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <linearGradient id="grad_{char_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{col_start};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{col_end};stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="46" fill="url(#grad_{char_id})" stroke="#ffffff" stroke-width="2" />
  <circle cx="50" cy="50" r="40" fill="none" stroke="#ffffff" stroke-width="1" stroke-dasharray="3,3" opacity="0.6" />
  <text x="50" y="58" font-family="'Segoe UI', Roboto, sans-serif" font-size="28" fill="#ffffff" text-anchor="middle" font-weight="bold" letter-spacing="1">
    {initial}
  </text>
</svg>"""

    with open(avatar_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    # Update visualizer record
    char_found["avatarUrl"] = f"/api/v1/projects/{project_id}/visualizer/assets/{avatar_filename}"
    char_found["imageStatus"] = "generated"
    _save_visualizer_data(project["filepath"], data)
    
    return {"avatarUrl": char_found["avatarUrl"]}

@router.get("/api/v1/projects/{project_id}/visualizer/assets/{filename}")
def get_visualizer_asset(project_id: str, filename: str, request: Request):
    """安全读取项目可视化资源 (头像 SVG、生成概念图等)"""
    project = _check_project(project_id, request)
    asset_path = os.path.abspath(os.path.join(project["filepath"], "visualizer_assets", filename))
    
    # Path traversal validation
    project_root = os.path.abspath(project["filepath"])
    if not asset_path.startswith(project_root + os.sep):
        raise HTTPException(status_code=400, detail="非法访问外部路径")
        
    if not os.path.exists(asset_path):
        raise HTTPException(status_code=404, detail="图片资源未找到")
        
    media_type = "image/svg+xml" if filename.endswith(".svg") else "image/png"
    return FileResponse(asset_path, media_type=media_type)
