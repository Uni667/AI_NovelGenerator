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
        temperature=0.7,
    )

def _generate_markdown_aspect(book_text: str, config: dict, aspect: str) -> str:
    llm = _get_llm(config)
    prompt = f"""请分析以下小说正文的【{aspect}】。
要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。
以 Markdown 格式输出分析结果。

正文内容：
{book_text}
"""
    try:
        return str(llm.invoke(prompt))
    except Exception as e:
        logger.error(f"Failed to generate {aspect}: {e}")
        return f"# {aspect}\n分析失败: {str(e)}"

def generate_style_bible(book_text: str, config: dict) -> str:
    return _generate_markdown_aspect(book_text, config, "风格圣经(文风、用词、句式)")

def generate_pacing_rules(book_text: str, config: dict) -> str:
    return _generate_markdown_aspect(book_text, config, "节奏模型(信息释放、高潮铺垫)")

def generate_conflict_models(book_text: str, config: dict) -> str:
    return _generate_markdown_aspect(book_text, config, "冲突模型(反派塑造、压制与反杀)")

def generate_hook_models(book_text: str, config: dict) -> str:
    return _generate_markdown_aspect(book_text, config, "钩子模型(悬念设置、断章技巧)")

def generate_platform_adaptation(book_text: str, config: dict) -> str:
    return _generate_markdown_aspect(book_text, config, "平台适配(首章黄金三章、系统设定)")

def generate_anti_copy_rules(book_text: str, config: dict) -> str:
    return _generate_markdown_aspect(book_text, config, "防照抄规则(规避照搬剧情的具体准则)")
