import os
import logging
from backend.app.database import get_db
from backend.app.services.project_service import get_project
from novel_generator.character_import import build_character_import_preview, merge_character_description, preferred_character_status, normalize_character_name
from datetime import datetime

logger = logging.getLogger(__name__)

def sync_db_to_txt(project_id: str) -> None:
    """
    Query all characters from the database for a given project_id and write them to character_state.txt
    """
    try:
        # We need the project path
        # Note: In a larger app, get_project would require user_id, but for local novel generator we can bypass or pass a dummy
        # Let's query project directly from DB to get filepath if get_project needs user_id.
        with get_db() as conn:
            project = conn.execute("SELECT filepath FROM project WHERE id = ?", (project_id,)).fetchone()
            if not project:
                logger.error(f"Cannot sync DB to txt: Project {project_id} not found.")
                return
            
            filepath = project["filepath"]
            state_file = os.path.join(filepath, "character_state.txt")
            
            # Get characters
            rows = conn.execute(
                """SELECT name, description, status, first_appearance_chapter 
                   FROM character_profile 
                   WHERE project_id = ? 
                   ORDER BY 
                     CASE status WHEN 'appeared' THEN 0 WHEN 'planned' THEN 1 WHEN 'suggested' THEN 2 ELSE 3 END,
                     COALESCE(first_appearance_chapter, 999999)""",
                (project_id,)
            ).fetchall()
            
            if not rows:
                content = "（尚未生成角色状态）"
            else:
                lines = ["# 角色状态 (Character State)"]
                for row in rows:
                    name = row["name"]
                    desc = row["description"] or ""
                    status = row["status"]
                    first_app = row["first_appearance_chapter"]
                    
                    status_text = "已登场" if status == 'appeared' else "未登场"
                    app_text = f"第{first_app}章登场" if first_app else "登场时间未定"
                    
                    lines.append(f"## {name} ({status_text}, {app_text})")
                    lines.append(desc)
                    lines.append("")
                
                content = "\n".join(lines)
            
            with open(state_file, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"Successfully synced {len(rows)} characters to {state_file}")
    except Exception as e:
        logger.exception("Failed to sync db to txt")

def sync_txt_to_db(project_id: str) -> None:
    """
    Read character_state.txt and upsert the data into the database.
    This is called after LLM updates character_state.txt during chapter finalization.
    """
    try:
        with get_db() as conn:
            project = conn.execute("SELECT filepath FROM project WHERE id = ?", (project_id,)).fetchone()
            if not project:
                logger.error(f"Cannot sync txt to DB: Project {project_id} not found.")
                return
            
            filepath = project["filepath"]
            state_file = os.path.join(filepath, "character_state.txt")
            
            if not os.path.exists(state_file):
                return
                
            with open(state_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Load existing characters
            rows = conn.execute(
                "SELECT * FROM character_profile WHERE project_id = ?",
                (project_id,)
            ).fetchall()
            existing_chars = [dict(row) for row in rows]
            
            # Use character_import logic to parse candidates
            candidates = build_character_import_preview(content, existing_chars)
            
            now = datetime.now().isoformat()
            
            for candidate in candidates:
                if candidate.decision == "reject":
                    continue
                    
                candidate_dict = candidate.to_dict()
                candidate_name = candidate_dict.get("name", "").strip()
                normalized_name = normalize_character_name(candidate_name)
                
                # Check if exists
                existing_row = None
                for row in existing_chars:
                    if normalize_character_name(row["name"]) == normalized_name:
                        existing_row = row
                        break
                        
                description = candidate_dict.get("description", "").strip() or candidate_dict.get("raw_text", "").strip()
                
                if existing_row:
                    merged_description = merge_character_description(existing_row.get("description", ""), description)
                    merged_status = preferred_character_status(existing_row.get("status", ""), candidate_dict.get("status", "planned"))
                    first_appearance = existing_row.get("first_appearance_chapter")
                    candidate_chapter = candidate_dict.get("first_appearance_chapter")
                    if candidate_chapter and (not first_appearance or candidate_chapter < first_appearance):
                        first_appearance = candidate_chapter
                        
                    conn.execute(
                        """UPDATE character_profile
                           SET description = ?, status = ?, first_appearance_chapter = ?, updated_at = ?
                           WHERE id = ? AND project_id = ?""",
                        (
                            merged_description[:1000],
                            merged_status,
                            first_appearance,
                            now,
                            existing_row["id"],
                            project_id,
                        ),
                    )
                else:
                    conn.execute(
                        """INSERT INTO character_profile
                           (project_id, name, description, status, source, first_appearance_chapter, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            project_id,
                            candidate_name,
                            description[:1000],
                            candidate_dict.get("status", "planned"),
                            "ai",
                            candidate_dict.get("first_appearance_chapter"),
                            now,
                        ),
                    )
            logger.info(f"Successfully synced txt to db for project {project_id}")
    except Exception as e:
        logger.exception("Failed to sync txt to db")
