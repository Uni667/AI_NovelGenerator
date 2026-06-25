import json
import logging
from backend.app.services import model_runtime

logger = logging.getLogger(__name__)

def _get_llm(config: dict):
    provider = config.get("provider", "openai")
    api_key = config.get("api_key", "dummy")
    base_url = config.get("base_url", "http://dummy")
    model_name = config.get("model", "gpt-4")
    
    return model_runtime.create_chat_adapter_from_config(
        interface_format=model_runtime._provider_to_interface(provider),
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=0.3, # low temp for JSON extraction
    )

def generate_scene_patterns(book_text: str, config: dict) -> list:
    """提取场景模式 (JSON array)"""
    llm = _get_llm(config)
    prompt = f"""请分析以下小说正文内容，提取其中的典型场景模式。
要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。
输出必须是有效的 JSON 数组，每个元素包含 pattern_name, description, trigger, resolution 字段。不要输出多余解释。

正文内容：
{book_text}
"""
    try:
        result = llm.invoke(prompt)
        text = str(result)
        # Extract json array if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to generate scene patterns: {e}")
        return []

def generate_plot_structure(book_text: str, config: dict) -> str:
    llm = _get_llm(config)
    prompt = f"""请分析以下小说正文的整体结构。
要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。
以 Markdown 格式输出 plot_structure 分析。

正文内容：
{book_text}
"""
    return str(llm.invoke(prompt))

def generate_character_arcs(book_text: str, config: dict) -> str:
    llm = _get_llm(config)
    prompt = f"""请分析以下小说正文的人物弧光。
要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。
以 Markdown 格式输出人物弧光分析。

正文内容：
{book_text}
"""
    return str(llm.invoke(prompt))
