import os
import datetime
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.database import get_db

router = APIRouter(tags=["知识库"])


@router.post("/api/v1/projects/{project_id}/knowledge/upload")
async def upload_knowledge(project_id: str, request: Request, file: UploadFile = File(...)):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    from novel_generator.knowledge import import_knowledge_file
    knowledge_dir = os.path.join(project["filepath"], "knowledge")
    os.makedirs(knowledge_dir, exist_ok=True)
    file_path = os.path.join(knowledge_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_file (project_id, filename, filepath, file_size, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, file.filename, file_path, os.path.getsize(file_path), now)
        )

    try:
        result = import_knowledge_file(file_path, project["filepath"])
        return {"message": result if result else "导入完成"}
    except Exception as e:
        return {"message": f"文件已保存，但向量库导入失败: {str(e)}"}


@router.delete("/api/v1/projects/{project_id}/knowledge/clear-vector")
def clear_vector_db(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    from novel_generator.vectorstore_utils import clear_vector_store
    clear_vector_store(project["filepath"])

    with get_db() as conn:
        conn.execute(
            "UPDATE knowledge_file SET imported = 0 WHERE project_id = ?",
            (project_id,)
        )

    return {"message": "向量库已清空"}
