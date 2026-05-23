import json
import logging
from typing import List, Dict, Any
from novel_generator.prompts.material_prompts import (
    MATERIAL_DECOMPOSITION_PROMPT,
    MATERIAL_DIAGNOSIS_PROMPT,
    MATERIAL_OPTIMIZE_PROMPT,
)
from novel_generator.commercial_profiles import get_platform_profile

logger = logging.getLogger(__name__)

class MaterialPipeline:
    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    def decompose(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        阶段二：解构原始文本为结构化实体
        """
        prompt = MATERIAL_DECOMPOSITION_PROMPT.format(raw_material=raw_text)
        try:
            result = self.llm.invoke(prompt)
            # 提取 JSON
            json_start = result.find("[")
            json_end = result.rfind("]") + 1
            if json_start != -1 and json_end != -1:
                return json.loads(result[json_start:json_end])
            else:
                logger.error(f"无法解析的解构结果: {result[:200]}")
                return []
        except Exception as e:
            logger.exception("素材解构失败")
            raise e

    def diagnose(self, entity: Dict[str, Any], platform: str = "tomato") -> Dict[str, Any]:
        """
        阶段二：对解构后的单一实体进行“X光体检”
        """
        profile = get_platform_profile(platform)
        
        # 简单提取画像规则，避免出错
        platform_loves = profile.get("pacing_rules", "爽快、节奏紧凑")
        platform_hates = profile.get("forbidden_tropes", "慢热、送女、文青、无主线")
        compliance_rules = "严禁涉黄、涉政、过度血腥暴力、违背核心价值观的内容"
        
        prompt = MATERIAL_DIAGNOSIS_PROMPT.format(
            platform_name=profile.get("name", platform),
            platform_loves=platform_loves,
            platform_hates=platform_hates,
            compliance_rules=compliance_rules,
            entity_type=entity.get("type", "unknown"),
            entity_title=entity.get("title", ""),
            entity_content=entity.get("content", "")
        )
        
        try:
            result = self.llm.invoke(prompt)
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start != -1 and json_end != -1:
                return json.loads(result[json_start:json_end])
            else:
                return {
                    "score": 50,
                    "is_compliant": True,
                    "has_toxic_tropes": False,
                    "issues": ["无法解析诊断结果"],
                    "missing_elements": [],
                    "suggestion": "诊断生成失败"
                }
        except Exception as e:
            logger.exception(f"实体诊断失败: {entity.get('title')}")
            raise e

    def optimize(self, entity: Dict[str, Any], diagnosis: Dict[str, Any], user_instruction: str = "") -> str:
        """
        阶段三：基于体检报告进行补全和抛光
        """
        prompt = MATERIAL_OPTIMIZE_PROMPT.format(
            entity_title=entity.get("title", ""),
            entity_content=entity.get("content", ""),
            diagnosis_report=json.dumps(diagnosis, ensure_ascii=False, indent=2),
            user_instruction=user_instruction or "请修复问题并扩写细节"
        )
        try:
            result = self.llm.invoke(prompt)
            return result.strip()
        except Exception as e:
            logger.exception(f"实体优化失败: {entity.get('title')}")
            raise e
