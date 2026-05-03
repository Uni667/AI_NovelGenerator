#novel_generator/knowledge.py
# -*- coding: utf-8 -*-
"""
知识文件导入至向量库（advanced_split_content、import_knowledge_file）
"""
import os
import logging
import re
import traceback
import warnings
from utils import read_file

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_nltk = _Document = None
_load_vs = _init_vs = None

def _ensure_nltk():
    global _nltk
    if _nltk is None:
        import nltk as _n
        _nltk = _n

def _ensure_langchain():
    global _Document
    if _Document is None:
        from langchain.docstore.document import Document as _d
        _Document = _d

def _ensure_vectorstore():
    global _load_vs, _init_vs
    if _load_vs is None:
        from novel_generator.vectorstore_utils import load_vector_store as _l, init_vector_store as _i
        _load_vs = _l
        _init_vs = _i

# 禁用特定的Torch警告
warnings.filterwarnings('ignore', message='.*Torch was not compiled with flash attention.*')
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def advanced_split_content(content: str, similarity_threshold: float = 0.7, max_length: int = 500) -> list:
    """使用基本分段策略"""
    _ensure_nltk()
    try:
        sentences = _nltk.sent_tokenize(content)
    except Exception:
        sentences = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    if not sentences:
        return []

    final_segments = []
    current_segment = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        if current_length + sentence_length > max_length:
            if current_segment:
                final_segments.append(" ".join(current_segment))
            current_segment = [sentence]
            current_length = sentence_length
        else:
            current_segment.append(sentence)
            current_length += sentence_length
    
    if current_segment:
        final_segments.append(" ".join(current_segment))
    
    return final_segments

def import_knowledge_file(
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    file_path: str,
    filepath: str
):
    logging.info(f"开始导入知识库文件: {file_path}, 接口格式: {embedding_interface_format}, 模型: {embedding_model_name}")
    if not os.path.exists(file_path):
        logging.warning(f"知识库文件不存在: {file_path}")
        return {"success": False, "message": f"知识库文件不存在: {file_path}", "paragraph_count": 0, "mode": "missing"}
    content = read_file(file_path)
    if not content.strip():
        logging.warning("知识库文件内容为空。")
        return {"success": False, "message": f"知识库文件为空: {file_path}", "paragraph_count": 0, "mode": "empty"}
    paragraphs = advanced_split_content(content)
    from embedding_adapters import create_embedding_adapter
    embedding_adapter = create_embedding_adapter(
        embedding_interface_format,
        embedding_api_key,
        embedding_url if embedding_url else "http://localhost:11434/api",
        embedding_model_name
    )
    _ensure_vectorstore()
    store = _load_vs(embedding_adapter, filepath)
    if not store:
        logging.info("Vector store does not exist or load failed. Initializing a new one for knowledge import...")
        store = _init_vs(embedding_adapter, paragraphs, filepath)
        if store:
            logging.info("知识库文件已成功导入至向量库(新初始化)。")
            return {
                "success": True,
                "message": "知识库文件已成功导入至向量库(新初始化)",
                "paragraph_count": len(paragraphs),
                "mode": "init",
            }
        else:
            logging.warning("知识库导入失败，跳过。")
            return {
                "success": False,
                "message": "知识库导入失败，向量库初始化未成功",
                "paragraph_count": len(paragraphs),
                "mode": "failed",
            }
    else:
        try:
            _ensure_langchain()
            docs = [_Document(page_content=str(p)) for p in paragraphs]
            store.add_documents(docs)
            logging.info("知识库文件已成功导入至向量库(追加模式)。")
            return {
                "success": True,
                "message": "知识库文件已成功导入至向量库(追加模式)",
                "paragraph_count": len(paragraphs),
                "mode": "append",
            }
        except Exception as e:
            logging.warning(f"知识库导入失败: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "message": f"知识库追加导入失败: {e}",
                "paragraph_count": len(paragraphs),
                "mode": "failed",
            }
