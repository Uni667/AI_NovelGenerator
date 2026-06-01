# -*- coding: utf-8 -*-

summarize_recent_chapters_prompt = """\
作为一名专业的小说编辑和知识管理专家，正在基于已完成的前三章内容和本章信息生成当前章节的精准摘要。请严格遵循以下工作流程：
前三章内容：
{combined_text}

当前章节信息：
第{novel_number}章《{chapter_title}》：
├── 本章定位：{chapter_role}
├── 核心作用：{chapter_purpose}
├── 悬念密度：{suspense_level}
├── 伏笔操作：{foreshadowing}
├── 认知颠覆：{plot_twist_level}
└── 本章简述：{chapter_summary}

下一章信息：
第{next_chapter_number}章《{next_chapter_title}》：
├── 本章定位：{next_chapter_role}
├── 核心作用：{next_chapter_purpose}
├── 悬念密度：{next_chapter_suspense_level}
├── 伏笔操作：{next_chapter_foreshadowing}
├── 认知颠覆：{next_chapter_plot_twist_level}
└── 本章简述：{next_chapter_summary}

**上下文分析阶段**：
1. 回顾前三章核心内容：
   - 第一章核心要素：[章节标题]→[核心冲突/理论]→[关键人物/概念]
   - 第二章发展路径：[已建立的人物关系]→[技术/情节进展]→[遗留伏笔]
   - 第三章转折点：[新出现的变量]→[世界观扩展]→[待解决问题]
2. 提取延续性要素：
   - 必继承要素：列出前3章中必须延续的3个核心设定
   - 可调整要素：识别2个允许适度变化的辅助设定

**当前章节摘要生成规则**：
1. 内容架构：
   - 继承权重：70%内容需与前3章形成逻辑递进
   - 创新空间：30%内容可引入新要素，但需标注创新类型（如：技术突破/人物黑化）
2. 结构控制：
   - 采用"承继→发展→铺垫"三段式结构
   - 每段含1个前文呼应点+1个新进展
3. 预警机制：
   - 若检测到与前3章设定冲突，用[!]标记并说明
   - 对开放式发展路径，提供2种合理演化方向

现在请你基于目前故事的进展，完成以下两件事：
用最多800字，写一个简洁明了的「当前章节摘要」；

请按如下格式输出（不需要额外解释）：
当前章节摘要: <这里写当前章节摘要>
"""

first_chapter_draft_prompt = """\
你是网文平台主编 + 商业化编辑 + 连载节奏医生。现在开始创作第 {novel_number} 章《{chapter_title}》。

本章定位：{chapter_role}
核心作用：{chapter_purpose}
悬念密度：{suspense_level}
伏笔操作：{foreshadowing}
认知颠覆：{plot_twist_level}
本章简述：{chapter_summary}

可用元素：
- 核心人物(可能未指定)：{characters_involved}
- 关键道具(可能未指定)：{key_items}
- 空间坐标(可能未指定)：{scene_location}
- 时间压力(可能未指定)：{time_constraint}

参考文档：
- 小说设定：
{novel_setting}

- 伏笔暗线台账：
{plot_arcs}

- 图谱记忆 (Graph RAG)：
{graph_context}

- 平台写作基准：
{platform_guidance}

完成第 {novel_number} 章的正文，字数要求{word_number}字，至少设计下方2个或以上具有动态张力的场景：
1. 对话场景：
   - 潜台词冲突（表面谈论A，实际博弈B）
   - 权力关系变化（通过非对称对话长度体现）

2. 动作场景：
   - 环境交互细节（至少3个感官描写）
   - 节奏控制（短句加速+比喻减速）
   - 动作揭示人物隐藏特质

3. 心理场景：
   - 认知失调的具体表现（行为矛盾）
   - 隐喻系统的运用（连接世界观符号）
   - 决策前的价值天平描写

4. 环境场景：
   - 空间透视变化（宏观→微观→异常焦点）
   - 非常规感官组合（如”听见阳光的重量”）
   - 动态环境反映心理（环境与人物心理对应）

平台连载自查（不要输出到正文）：
- 前200字是否已进入冲突/异样/危险/欲望/悬念？
- 本章是否有至少一个爽点或情绪冲击点？
- 设定是否通过事件和选择落地，而非一次性倾倒？
- 结尾是否留下了追读钩子？

作者控制边界（必须遵守）：
- 不得修改用户已明确的世界观、人物关系、主线立意和感情走向
- 不写真实人物谣言、不消费灾难、不硬蹭敏感事件
- 不生成仇恨、色情、违法擦边、极端暴力内容
- 不确定处只给备选方案，不替作者做最终决定

格式要求：
- 仅返回章节正文文本；
- 不使用分章节小标题；
- 不要使用markdown格式。
- 禁止出现提纲腔、总结腔、解释腔，不要写成”她知道/他明白/这一刻意味着”这种空泛归纳。
- 禁止连续使用工整排比句、模板化短句堆砌、过多抽象比喻来冒充文采。
- 人物说话必须带身份差异和当下情绪，不要所有角色都像同一个作者在发言。
- 心理描写要落在当下反应和动作选择上，不要长段分析人物内心。
- 能用动作、物件、环境细节说明的，不要直接替作者解释。

额外指导(可能未指定)：{user_guidance}
"""

next_chapter_draft_prompt = """\
参考文档：
└── 前文摘要：
    {global_summary}

└── 前章结尾段：
    {previous_chapter_excerpt}

└── 用户指导：
    {user_guidance}

└── 角色状态：
    {character_state}

└── 伏笔暗线台账：
    {plot_arcs}

└── 图谱记忆 (Graph RAG)：
    {graph_context}

└── 当前章节摘要：
    {short_summary}

└── 平台写作基准：
    {platform_guidance}

当前章节信息：
第{novel_number}章《{chapter_title}》：
├── 章节定位：{chapter_role}
├── 核心作用：{chapter_purpose}
├── 悬念密度：{suspense_level}
├── 伏笔设计：{foreshadowing}
├── 转折程度：{plot_twist_level}
├── 章节简述：{chapter_summary}
├── 字数要求：{word_number}字
├── 核心人物：{characters_involved}
├── 关键道具：{key_items}
├── 场景地点：{scene_location}
└── 时间压力：{time_constraint}

下一章节目录
第{next_chapter_number}章《{next_chapter_title}》：
├── 章节定位：{next_chapter_role}
├── 核心作用：{next_chapter_purpose}
├── 悬念密度：{next_chapter_suspense_level}
├── 伏笔设计：{next_chapter_foreshadowing}
├── 转折程度：{next_chapter_plot_twist_level}
└── 章节简述：{next_chapter_summary}

知识库参考：（按优先级应用）
{filtered_context}

🎯 知识库应用规则：
1. 内容分级：
   - 写作技法类（优先）：
     ▸ 场景构建模板
     ▸ 对话写作技巧
     ▸ 悬念营造手法
   - 设定资料类（选择性）：
     ▸ 独特世界观元素
     ▸ 未使用过的技术细节
   - 禁忌项类（必须规避）：
     ▸ 已在前文出现过的特定情节
     ▸ 重复的人物关系发展

2. 使用限制：
   ● 禁止直接复制已有章节的情节模式
   ● 历史章节内容仅允许：
     → 参照叙事节奏（不超过20%相似度）
     → 延续必要的人物反应模式（需改编30%以上）
   ● 第三方写作知识优先用于：
     → 增强场景表现力（占知识应用的60%以上）
     → 创新悬念设计（至少1处新技巧）

3. 冲突检测：
   ⚠️ 若检测到与历史章节重复：
     - 相似度>40%：必须重构叙事角度
     - 相似度20-40%：替换至少3个关键要素
     - 相似度<20%：允许保留核心概念但改变表现形式

你是网文平台主编 + 商业化编辑 + 连载节奏医生。现在开始创作第 {novel_number} 章正文。

你必须严格遵循用户指导、当前章节摘要、伏笔暗线台账和平台写作基准，
确保章节内容与前文摘要、前章结尾段衔接流畅，
与下一章目录保持上下文完整性，杜绝逻辑漏洞。

平台连载自查（不要输出到正文）：
- 前200字是否已进入冲突/异样/危险/欲望/悬念？
- 本章是否有至少一个爽点或情绪冲击点？
- 设定是否通过事件和选择落地，而非一次性倾倒？
- 结尾是否留下了追读钩子？

作者控制边界（必须遵守）：
- 不得修改用户已明确的世界观、人物关系、主线立意和感情走向
- 不写真实人物谣言、不消费灾难、不硬蹭敏感事件
- 不生成仇恨、色情、违法擦边、极端暴力内容
- 不确定处只给备选方案，不替作者做最终决定

开始完成第 {novel_number} 章的正文，字数要求{word_number}字，
内容生成严格遵循：
-用户指导
-当前章节摘要
-当前章节信息
-伏笔暗线台账
-无逻辑漏洞,
确保章节内容与前文摘要、前章结尾段衔接流畅、下一章目录保证上下文完整性，

格式要求：
- 仅返回章节正文文本；
- 不使用分章节小标题；
- 不要使用markdown格式。
- 禁止出现提纲腔、总结腔、解释腔，不要写成”她知道/他明白/这一刻意味着”这种空泛归纳。
- 禁止连续使用工整排比句、模板化短句堆砌、过多抽象比喻来冒充文采。
- 人物说话必须带身份差异和当下情绪，不要所有角色都像同一个作者在发言。
- 心理描写要落在当下反应和动作选择上，不要长段分析人物内心。
- 能用动作、物件、环境细节说明的，不要直接替作者解释。
"""

platform_chapter_guidance_prompt = """\
平台写作基准：{platform_label}

平台生成要求：
{platform_rules}

写作前内部自检清单（不要把清单输出到正文里）：
1. 开头前200字必须尽快进入冲突、异样、威胁、欲望或强悬念，避免先铺背景。
2. 信息密度优先，少写空镜、泛泛心理、与主线无关的景物描写。
3. 每个场景都要推进至少一项：冲突升级、人物关系变化、信息揭露、伏笔埋设或回收。
4. 章节结尾必须留下明确的追读钩子，优先使用危机型、揭秘型、欲望型、反转型之一。
5. 如果平台强调爽点/情绪冲击，就优先保证读者能在3秒内感知核心刺激点。
"""



first_chapter_draft_prompt_memory_aware = """\
你是网文平台主编 + 商业化编辑 + 连载节奏医生。现在开始创作第 {novel_number} 章《{chapter_title}》。

【当前章节任务】
本章定位：{chapter_role}
核心作用：{chapter_purpose}
悬念密度：{suspense_level}
伏笔操作：{foreshadowing}
认知颠覆：{plot_twist_level}
本章简述：{chapter_summary}

【本章禁止事项】
{forbidden_violations}
- 不得修改用户已明确的世界观、人物关系、主线立意和感情走向
- 不得写出未揭露的真实姓名或过早揭露来历
- 不确定处只给备选方案，不替作者做最终决定

【不可违背事实】
以下内容来自项目初期设定，必须遵守，不能否定或重写：
{locked_previous_facts}

【人物状态】
以下人物状态来自已合并核心设定：
{character_state_brief}

【称呼规则】
以下称呼规则必须严格遵守：
{name_usage_rules_brief}

【伏笔与秘密状态】
{plot_threads_brief}

参考文档：
- 全局摘要：
{global_summary}

- 额外指导：
{user_guidance}

完成第 {novel_number} 章的正文，字数要求{word_number}字。
格式要求：
- 仅返回章节正文文本；
- 不使用分章节小标题；
- 不要使用markdown格式。
"""

next_chapter_draft_prompt_memory_aware = """\
你是网文平台主编 + 商业化编辑 + 连载节奏医生。现在开始创作第 {novel_number} 章《{chapter_title}》。

【当前章节任务】
本章定位：{chapter_role}
核心作用：{chapter_purpose}
悬念密度：{suspense_level}
伏笔操作：{foreshadowing}
认知颠覆：{plot_twist_level}
本章简述：{chapter_summary}
字数要求：{word_number}字

【本章禁止事项】
{forbidden_violations}
- 不得修改用户已明确的世界观、人物关系、主线立意和感情走向
- 不得写出未揭露的真实姓名或过早揭露来历
- 不得推翻已定稿章节发生过的事件

【不可违背事实】
以下内容来自已定稿章节，必须遵守，不能否定或遗忘：
{locked_previous_facts}

【人物状态】
以下人物状态来自已合并 character_state.json：
{character_state_brief}

【称呼规则】
以下称呼规则必须严格遵守：
{name_usage_rules_brief}

【伏笔与秘密状态】
{plot_threads_brief}

前文参考：
- 全局剧情摘要：
{global_summary}

- 前章结尾段：
{previous_chapter_excerpt}

- 额外指导：
{user_guidance}

开始完成第 {novel_number} 章的正文，字数要求{word_number}字。
格式要求：
- 仅返回章节正文文本；
- 不使用分章节小标题；
- 不要使用markdown格式。
- 禁止出现提纲腔、总结腔、解释腔。
"""
