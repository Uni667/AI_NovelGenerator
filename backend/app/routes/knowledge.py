import datetime
import os

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.services import project_service
from novel_generator.knowledge import import_knowledge_file
from novel_generator.vectorstore_utils import clear_vector_store

router = APIRouter(tags=["知识库"])


def _check_project(project_id: str, request: Request) -> tuple[dict, str]:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project, user_id


def _resolve_embedding_config(user_id: str, project_id: str) -> dict:
    """Get embedding runtime config through ModelRuntimeService. Returns dict with keys for downstream."""
    from backend.app.services.model_runtime import get_runtime_config, ConfigError, _provider_to_interface

    try:
        rt = get_runtime_config(user_id, "embedding", project_id)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "api_key": rt.api_key,
        "base_url": rt.base_url,
        "model_name": rt.model,
        "interface_format": _provider_to_interface(rt.provider),
    }


def _fetch_knowledge_file(project_id: str, user_id: str, file_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_file WHERE id = ? AND project_id = ? AND user_id = ?",
            (file_id, project_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def _set_imported(project_id: str, user_id: str, file_id: int, imported: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE knowledge_file SET imported = ? WHERE id = ? AND project_id = ? AND user_id = ?",
            (imported, file_id, project_id, user_id),
        )


def _list_files(project_id: str, user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge_file WHERE project_id = ? AND user_id = ? ORDER BY created_at DESC",
            (project_id, user_id),
        ).fetchall()
        return [dict(row) for row in rows]


def _import_file_to_vector_store(project: dict, embedding_config: dict, file_path: str) -> dict:
    if not embedding_config:
        return {
            "success": False,
            "message": "未找到可用的 Embedding 配置，文件已保存但尚未导入向量库",
            "mode": "pending",
        }

    return import_knowledge_file(
        embedding_config.get("api_key", ""),
        embedding_config.get("base_url", ""),
        embedding_config.get("interface_format", "OpenAI"),
        embedding_config.get("model_name", ""),
        file_path,
        project["filepath"],
    )


def _rebuild_vector_store(project: dict, user_id: str) -> dict:
    embedding_config = _resolve_embedding_config(user_id, project["id"])
    remaining_files = _list_files(project["id"], user_id)
    imported_files = [row for row in remaining_files if row.get("imported") and os.path.exists(row.get("filepath", ""))]

    clear_vector_store(project["filepath"])
    if not imported_files:
        return {
            "success": True,
            "message": "向量库已清空，当前没有可重建的知识文件",
            "reimported": 0,
        }

    if not embedding_config:
        with get_db() as conn:
            conn.execute(
                "UPDATE knowledge_file SET imported = 0 WHERE project_id = ? AND user_id = ?",
                (project["id"], user_id),
            )
        return {
            "success": False,
            "message": "已清空向量库，但当前没有可用的 Embedding 配置，无法重建索引",
            "reimported": 0,
        }

    rebuilt = 0
    failures = []
    for row in imported_files:
        result = _import_file_to_vector_store(project, embedding_config, row["filepath"])
        if result.get("success"):
            rebuilt += 1
            _set_imported(project["id"], user_id, row["id"], 1)
        else:
            failures.append({"file_id": row["id"], "filename": row["filename"], "message": result.get("message", "")})
            _set_imported(project["id"], user_id, row["id"], 0)

    return {
        "success": not failures,
        "message": "向量库已重建" if not failures else "向量库重建部分失败",
        "reimported": rebuilt,
        "failures": failures,
    }


@router.get("/api/v1/projects/{project_id}/knowledge/files")
def list_knowledge_files(project_id: str, request: Request):
    _project, user_id = _check_project(project_id, request)
    return _list_files(project_id, user_id)


@router.post("/api/v1/projects/{project_id}/knowledge/upload")
async def upload_knowledge(project_id: str, request: Request, file: UploadFile = File(...)):
    project, user_id = _check_project(project_id, request)
    knowledge_dir = os.path.join(project["filepath"], "knowledge")
    os.makedirs(knowledge_dir, exist_ok=True)
    file_path = os.path.join(knowledge_dir, file.filename)

    with open(file_path, "wb") as output:
        output.write(await file.read())

    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO knowledge_file (user_id, project_id, filename, filepath, file_size, imported, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, project_id, file.filename, file_path, os.path.getsize(file_path), 0, now),
        )
        file_id = cursor.lastrowid

    embedding_config = _resolve_embedding_config(user_id, project_id)
    import_result = _import_file_to_vector_store(project, embedding_config, file_path)
    if import_result.get("success"):
        _set_imported(project_id, user_id, file_id, 1)
        return {
            "message": import_result.get("message", "导入完成"),
            "file": {"id": file_id, "filename": file.filename, "filepath": file_path},
            "imported": True,
        }

    return {
        "message": import_result.get("message", "文件已保存，但向量库导入失败"),
        "file": {"id": file_id, "filename": file.filename, "filepath": file_path},
        "imported": False,
    }


@router.post("/api/v1/projects/{project_id}/knowledge/files/{file_id}/reimport")
def reimport_knowledge_file(project_id: str, file_id: int, request: Request):
    project, user_id = _check_project(project_id, request)
    row = _fetch_knowledge_file(project_id, user_id, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="知识库文件不存在")
    if not os.path.exists(row["filepath"]):
        raise HTTPException(status_code=404, detail=f"知识库文件已丢失: {row['filename']}")

    _set_imported(project_id, user_id, file_id, 1)
    result = _rebuild_vector_store(project, user_id)
    return {
        "message": result.get("message", "重导完成"),
        "file": row["filename"],
        "result": result,
    }


@router.delete("/api/v1/projects/{project_id}/knowledge/files/{file_id}")
def delete_knowledge_file(project_id: str, file_id: int, request: Request):
    project, user_id = _check_project(project_id, request)
    row = _fetch_knowledge_file(project_id, user_id, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="知识库文件不存在")

    filepath = os.path.abspath(row["filepath"])
    project_root = os.path.abspath(project["filepath"])
    if not filepath.startswith(project_root + os.sep):
        raise HTTPException(status_code=400, detail="文件路径非法")

    with get_db() as conn:
        conn.execute(
            "DELETE FROM knowledge_file WHERE id = ? AND project_id = ? AND user_id = ?",
            (file_id, project_id, user_id),
        )

    if os.path.exists(filepath):
        os.remove(filepath)

    rebuild_result = _rebuild_vector_store(project, user_id)
    return {
        "message": f"知识库文件已删除: {row['filename']}",
        "file": row["filename"],
        "rebuild": rebuild_result,
    }


@router.delete("/api/v1/projects/{project_id}/knowledge/clear-vector")
def clear_vector_db(project_id: str, request: Request):
    project, user_id = _check_project(project_id, request)
    clear_vector_store(project["filepath"])

    with get_db() as conn:
        conn.execute(
            "UPDATE knowledge_file SET imported = 0 WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
        )

    return {"message": "向量库已清空"}
