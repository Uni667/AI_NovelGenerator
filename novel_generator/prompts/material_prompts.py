# novel_generator/prompts/material_prompts.py

from novel_generator.commercial_profiles import get_platform_profile

MATERIAL_DECOMPOSITION_PROMPT = """你是一个资深的网文IP设定架构师。你的任务是将一段散乱的原始文字素材，拆解重构为清晰、标准的结构化数据。

## 目标
识别文字中提及的关键实体，将其分类为以下几种类型：
1. `character`: 角色卡（包含姓名、身份、性格、核心动机）
2. `world_rule`: 世界观规则（包含势力、力量体系、特殊物品、历史背景等）
3. `plot_arc`: 剧情线/大纲片段（包含起因、发展、高潮、结果）
4. `hook`: 钩子/爽点（任何吸引眼球的核心卖点）

## 原始素材
{raw_material}

## 输出要求
请严格输出一个 JSON 数组，数组中的每个对象代表一个拆解出的实体，格式如下：
[
  {{
    "id": "随机唯一的字符串ID",
    "type": "character | world_rule | plot_arc | hook",
    "title": "实体的短标题（如：主角李明、练气期设定、退婚风波）",
    "content": "实体的详细内容整理，不少于50字",
    "tags": ["标签1", "标签2"]
  }}
]

注意：
- 只输出合法的 JSON 数组，不要任何多余的解释。
- 确保 JSON 格式可以被 json.loads 解析。
"""

MATERIAL_DIAGNOSIS_PROMPT = """你是一个身经百战的网文平台金牌责编。你的任务是使用“X光扫描”为一段拆解好的素材进行全方位体检，特别是对比目标平台的读者口味和审核规则。

## 平台画像与红线
目标平台：{platform_name}
平台读者最爱：{platform_loves}
平台读者最恨（毒点）：{platform_hates}
合规红线：{compliance_rules}

## 待诊断实体
实体类型：{entity_type}
实体标题：{entity_title}
实体内容：{entity_content}

## 诊断标准
1. **查漏补缺 (Completeness)**：内容是否有重大逻辑缺失？（如：反派没动机，主角没金手指，世界观没力量上限）。
2. **防毒点 (Toxicity Check)**：是否踩中了目标平台读者最恨的毒点？（如番茄忌讳慢热、送女、憋屈）。
3. **平台口味对齐 (Platform Alignment)**：是否符合该平台的节奏和爽点要求？
4. **合规审查 (Compliance)**：是否有违规涉黄涉政倾向？

## 输出格式
请输出合法的 JSON，格式如下：
{{
  "score": 综合评分(0-100),
  "is_compliant": true/false (如果不合规必须设为false),
  "has_toxic_tropes": true/false (如果踩雷必须设为false),
  "issues": ["问题1", "问题2"],
  "missing_elements": ["缺失元素1", "缺失元素2"],
  "suggestion": "一两句话的核心优化建议"
}}
"""

MATERIAL_OPTIMIZE_PROMPT = """你是一个专业的网文执笔手。根据主编的“X光体检报告”，你需要对这段原素材进行重写和优化补全。

## 原始素材
标题：{entity_title}
内容：{entity_content}

## 体检报告与优化方向
{diagnosis_report}
用户额外要求：{user_instruction}

## 任务要求
1. 如果体检报告指出了“毒点”，必须在重写中彻底消除。
2. 如果提示“缺漏”，必须基于合理想象进行补全。
3. 请使用专业、精炼的网文设定集语言（不要写成散文，要条理清晰）。
4. 字数控制在原内容的 1.5 倍以内。

## 输出格式
仅输出优化重写后的【详细内容文本】，不需要输出标题，不要包含其他解释。"""
