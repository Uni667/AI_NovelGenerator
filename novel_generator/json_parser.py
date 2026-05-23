# -*- coding: utf-8 -*-
"""
鲁棒的 JSON 提取工具
用于在 LLM 可能返回前后文或者 Markdown 代码块的情况下，
安全地提取并解析 JSON 数据。
"""
import json
import re
import logging

logger = logging.getLogger(__name__)

def extract_json_from_text(text: str):
    """
    从可能包含无关文本或 Markdown 代码块的字符串中提取 JSON 对象或数组。
    如果解析失败，返回 None。
    """
    if not text:
        return None

    # 1. 如果带有 Markdown 的 json 块，优先尝试提取块内内容
    markdown_json_pattern = r'```(?:json)?\s*(.*?)\s*```'
    matches = re.findall(markdown_json_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    for match in matches:
        match = match.strip()
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # 2. 回退：直接使用正则匹配最外层的 {} 或 []
    # 这个正则试图找到以 { 或 [ 开头，并以 } 或 ] 结尾的最长字符串
    # 为了避免复杂的平衡组，我们用一个粗略的非贪婪查找，
    # 或者直接找到第一个 { / [ 和最后一个 } / ]
    
    start_obj = text.find('{')
    end_obj = text.rfind('}')
    
    start_arr = text.find('[')
    end_arr = text.rfind(']')

    # 判断是对象还是数组
    candidate = ""
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            # 都存在，看哪个先出现
            if start_obj < start_arr:
                candidate = text[start_obj:end_obj + 1]
            else:
                candidate = text[start_arr:end_arr + 1]
        else:
            candidate = text[start_obj:end_obj + 1]
    elif start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        candidate = text[start_arr:end_arr + 1]
        
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON 提取回退解析失败: {e}")
            
    return None
