import os
import datetime
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.app.services import project_service
from backend.app.database import get_db
from novel_generator.knowledge import import_knowledge_file
from novel_generator.vectorstore_utils import clear_vector_store

router = APIRouter(tags=["知识库"])


@router.post("/api/v1/projects/{project_id}/knowledge/upload")
async def upload_knowledge(project_id: str, file: UploadFile = File(...)):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    # 保存到项目目录
    knowledge_dir = os.path.join(project["filepath"], "knowledge")
    os.makedirs(knowledge_dir, exist_ok=True)
    file_path = os.path.join(knowledge_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # 记录到数据库
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_file (project_id, filename, filepath, file_size, imported, created_at) VALUES (?,?,?,?,?,?)",
            (project_id, file.filename, file_path, len(content), 0, now)
        )

    # 尝试导入向量库
    try:
        from backend.app.dependencies import get_config as get_global_config
        config = get_global_config()
        last_emb = config.get("last_embedding_interface_format", "OpenAI")
        emb_conf = config.get("embedding_configs", {}).get(last_emb, {})

        import_knowledge_file(
            embedding_api_key=emb_conf.get("api_key", ""),
            embedding_url=emb_conf.get("base_url", "https://api.openai.com/v1"),
            embedding_interface_format=emb_conf.get("interface_format", "OpenAI"),
            embedding_model_name=emb_conf.get("model_name", "text-embedding-ada-002"),
            file_path=file_path,
            filepath=project["filepath"]
        )

        with get_db() as conn:
            conn.execute(
                "UPDATE knowledge_file SET imported=1 WHERE project_id=? AND filename=?",
                (project_id, file.filename)
            )
        return {"message": f"文件 '{file.filename}' 已上传并导入向量库", "filename": file.filename}
    except Exception as e:
        return {"message": f"文件已上传但向量库导入失败: {str(e)}", "filename": file.filename}


@router.delete("/api/v1/projects/{project_id}/knowledge/clear-vector")
def clear_knowledge_vector(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if clear_vector_store(project["filepath"]):
        with get_db() as conn:
            conn.execute("UPDATE knowledge_file SET imported=0 WHERE project_id=?", (project_id,))
        return {"message": "向量库已清空"}
    return {"message": "向量库不存在或清空失败"}
