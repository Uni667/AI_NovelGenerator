# -*- coding: utf-8 -*-
"""
生成万界仙帝第61-80章
使用 DeepSeek API 直接生成，融入四项写作质量要求。
生成后同步到本地文件夹和在线服务器。
"""
import os
import sys
import json
import time
import re
import requests
from datetime import datetime

# 配置
API_KEY = "sk-f19e0657b95c40cda2d760b49bfc30c2"
API_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-v4-flash"
TEMPERATURE = 0.7
MAX_TOKENS = 8192

# 路径
PROJECT_PATH = r"C:\Users\Lenovo\Desktop\万界仙帝"
CHAPTERS_DIR = os.path.join(PROJECT_PATH, "章节")
SETTINGS_DIR = os.path.join(PROJECT_PATH, "设定")

# 在线后端配置
BACKEND_URL = "https://ai-novel-backend-production.up.railway.app"
PROJECT_ID = "ef1de677-1a9a-4f28-9516-554e5a53838a"
USERNAME = "wanjie_xiandi"
PASSWORD = "xk9mF2#pLq7vBn3"

# 写作质量要求
WRITING_QUALITY = """
【写作质量四项要求 - 必须严格遵守】

1. 角色出场要自然 — 不要生硬雷同，不要让角色突然出现然后就开始介绍身份背景
   - 角色应该通过事件、对话、环境交互自然引入
   - 避免"突然出现+旁白介绍"这种重复模式

2. 文笔需要提升 — 太"小白文"，需要更精炼有深度
   - 减少直白叙述，多用细节和行动展示
   - 适当使用修辞手法，但不要过度堆砌
   - 对话要有角色特色，避免千篇一律

3. 暗线铺垫要更长 — 不要这章引出下章就揭晓
   - 重要伏笔需要跨越多章逐步展开
   - 让读者有猜测和期待的空间
   - 揭晓时要有积累的冲击力

4. 人物形象通过事件深化 — 每个角色都要让读者有印象
   - 通过选择和行动展现性格，而非直接描述
   - 关键配角也要有记忆点
   - 事件中展现人物的矛盾、成长和独特性
"""

def read_file(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return ""

def save_chapter(chapter_num, content):
    """保存章节到本地"""
    filename = f"chapter_{chapter_num:04d}.txt"
    filepath = os.path.join(CHAPTERS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ 已保存本地: {filepath}")
    return filepath

def get_online_token():
    """获取在线后端认证令牌"""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        print(f"  ⚠ 登录失败: {resp.status_code} {resp.text[:100]}")
        return None
    except Exception as e:
        print(f"  ⚠ 无法连接在线后端: {e}")
        return None

def upload_to_server(chapter_num, content, token):
    """上传章节到在线服务器"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # 更新章节内容
        resp = requests.put(
            f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/chapters/{chapter_num}",
            json={"content": content, "status": "draft"},
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            print(f"  ✓ 已上传到服务器 (Ch {chapter_num})")
            return True
        else:
            print(f"  ⚠ 上传失败 Ch {chapter_num}: {resp.status_code} {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  ⚠ 上传异常 Ch {chapter_num}: {e}")
        return False

def call_llm(system_prompt, user_prompt, max_retries=3):
    """调用 DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": False
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{API_BASE}/chat/completions",
                headers=headers,
                json=payload,
                timeout=300
            )
            if resp.status_code == 200:
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                # 清理可能的思考标签
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                return content.strip()
            else:
                print(f"  ⚠ API 错误 (attempt {attempt+1}): {resp.status_code} {resp.text[:200]}")
                if attempt < max_retries - 1:
                    wait = 2 ** attempt * 5
                    print(f"  ⏳ 等待 {wait} 秒后重试...")
                    time.sleep(wait)
        except Exception as e:
            print(f"  ⚠ 请求异常 (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                print(f"  ⏳ 等待 {wait} 秒后重试...")
                time.sleep(wait)

    return None

def get_recent_chapters_context(num_chapters=5):
    """获取最近几章的内容作为上下文"""
    chapters = []
    for i in range(60 - num_chapters + 1, 61):
        filepath = os.path.join(CHAPTERS_DIR, f"chapter_{i:04d}.txt")
        content = read_file(filepath)
        if content:
            # 取每章前500字和后300字作为上下文
            if len(content) > 1000:
                summary = content[:500] + "\n...(中略)...\n" + content[-300:]
            else:
                summary = content
            chapters.append(f"【第{i}章摘要】\n{summary[:800]}")
    return "\n\n".join(chapters)

def get_chapter_blueprint(chapter_num):
    """从 Novel_directory.txt 提取指定章节的蓝图"""
    blueprint_file = os.path.join(SETTINGS_DIR, "Novel_directory.txt")
    blueprint_text = read_file(blueprint_file)

    # 查找对应章节的蓝图信息
    pattern = rf'\*\*第{chapter_num}章 - ([^*]+)\*\*\n(.*?)(?=\n\*\*第\d+章|$)'
    match = re.search(pattern, blueprint_text, re.DOTALL)
    if match:
        title = match.group(1).strip()
        details = match.group(2).strip()
        return title, details

    # 备用：逐行搜索
    lines = blueprint_text.split('\n')
    for i, line in enumerate(lines):
        if f'**第{chapter_num}章' in line:
            context_lines = []
            for j in range(i, min(i + 15, len(lines))):
                context_lines.append(lines[j])
                if j > i and '**第' in lines[j] and '章' in lines[j]:
                    break
            return line.strip(), '\n'.join(context_lines)

    return f"第{chapter_num}章", ""

def load_project_context():
    """加载项目全局上下文"""
    context = {}

    # 全局摘要
    global_summary = read_file(os.path.join(SETTINGS_DIR, "全局摘要.txt"))
    context["global_summary"] = global_summary[:3000] if global_summary else ""

    # 核心摘要
    core_summary = read_file(os.path.join(SETTINGS_DIR, "核心摘要.txt"))
    context["core_summary"] = core_summary[:2000] if core_summary else ""

    # 架构
    architecture = read_file(os.path.join(SETTINGS_DIR, "Novel_architecture.txt"))
    context["architecture"] = architecture[:2000] if architecture else ""

    # 角色设定
    characters = read_file(os.path.join(SETTINGS_DIR, "角色年卡.txt"))
    context["characters"] = characters[:3000] if characters else ""

    return context

def build_generation_prompt(chapter_num, chapter_title, chapter_blueprint, context):
    """构建生成提示词"""

    system_prompt = f"""你是一位资深网络小说作家，正在创作仙侠小说《万界仙帝》。

{WRITING_QUALITY}

【故事背景与设定】
主角：林尘 - 被家族抛弃后获得不朽皇帝种子传承，一步步崛起
女主：苏月 - 帝妃转世，体内有法器碎片，与林尘互相救赎
主要反派：东极帝君 - 万年前背叛不朽皇帝的四方帝君之首
配角：老乞丐(七大战将之一，已牺牲)、小不点(器灵)、南极帝君、北极帝君、西极帝君

【当前剧情阶段】
林尘已突破帝境，老乞丐已牺牲（第58章魂飞魄散），苏月觉醒了部分前世记忆（帝妃），
知道自己是帝妃转世。东极帝君的帝咒即将在第85天发作。
当前时间：第83-90天（百日倒计时接近尾声）

【本小说核心暗线】
1. 不朽皇帝的种子是双刃剑 - 既是传承也是陷阱
2. 苏月前世帝妃下毒真相 - 是皇帝的自杀式布局
3. 东极帝君对帝妃的执念 - 他做的一切都是为了让她"回来"
4. 母亲被囚禁在时空裂隙 - 林尘尚未知晓的全部真相
5. 四方帝君的帝咒连锁 - 不朽皇帝临死前的反噬

【章节生成要求】
1. 每章3000-5000字
2. 章节标题格式: "# 第X章 标题名"
3. 以倒计时天数开头（如"第83天。"）
4. 语言风格：冷峻克制、有画面感、对话有角色辨识度
5. 情节推进要紧凑，避免灌水
6. 暗线要跨章铺垫，本章埋的伏笔不要立刻回收
7. 战斗场景要有具体动作描写，不要"一拳打飞"式省略
8. 情感场景要有细节，通过动作和表情传达，避免直接描述情绪"""

    user_prompt = f"""请根据以下蓝图创作《万界仙帝》第{chapter_num}章。

【章节蓝图】
标题: {chapter_title}
{chapter_blueprint}

【前情提要 - 最近章节】
{context.get('recent_chapters', '')}

【全局剧情摘要】
{context.get('global_summary', '')[:1500]}

【核心角色当前状态】
{context.get('characters', '')[:1500]}

【本章特别注意事项】
- 严格按蓝图的核心事件和转折点来写
- 角色对话要有辨识度（林尘：冷峻果断，苏月：温柔坚韧，东极帝君：偏执疯狂）
- 暗线要持续推进但不急于揭晓
- 以倒计时天数开头（第83-90天的范围内）
- 篇幅控制在3000-5000字

请直接开始创作第{chapter_num}章正文，不需要额外的说明。"""

    return system_prompt, user_prompt

def generate_chapter(chapter_num, context, token=None):
    """生成单个章节"""
    print(f"\n{'='*60}")
    print(f"📝 正在生成第 {chapter_num} 章...")
    print(f"{'='*60}")

    # 获取蓝图
    chapter_title, chapter_blueprint = get_chapter_blueprint(chapter_num)
    print(f"  标题: {chapter_title}")

    # 获取最近章节上下文
    recent = get_recent_chapters_context(5)
    context["recent_chapters"] = recent

    # 构建提示词
    system_prompt, user_prompt = build_generation_prompt(
        chapter_num, chapter_title, chapter_blueprint, context
    )

    # 调用 LLM
    print(f"  ⏳ 正在调用 DeepSeek API...")
    start_time = time.time()
    content = call_llm(system_prompt, user_prompt)
    elapsed = time.time() - start_time

    if content:
        word_count = len(content)
        print(f"  ✓ 生成完成! 耗时: {elapsed:.1f}秒, 字数: {word_count}")

        # 确保以章节标题开头
        if not content.startswith("#"):
            content = f"# 第{chapter_num}章 {chapter_title}\n\n{content}"

        # 保存本地
        save_chapter(chapter_num, content)

        # 上传服务器
        if token:
            upload_to_server(chapter_num, content, token)
        else:
            print(f"  ⚠ 跳过上传（无认证令牌）")

        return content
    else:
        print(f"  ✗ 生成失败!")
        return None

def main():
    print("╔══════════════════════════════════════╗")
    print("║   万界仙帝 第61-80章 批量生成      ║")
    print("║   模型: DeepSeek V4 Flash           ║")
    print("╚══════════════════════════════════════╝")

    # 加载全局上下文
    print("\n📚 加载项目上下文...")
    context = load_project_context()
    print(f"  全局摘要: {len(context['global_summary'])} 字符")
    print(f"  核心摘要: {len(context['core_summary'])} 字符")
    print(f"  架构文件: {len(context['architecture'])} 字符")
    print(f"  角色设定: {len(context['characters'])} 字符")

    # 确保目录存在
    os.makedirs(CHAPTERS_DIR, exist_ok=True)

    # 获取在线令牌
    print("\n🔑 获取在线后端认证...")
    token = get_online_token()
    if token:
        print(f"  ✓ 已登录在线后端 (项目: {PROJECT_ID})")
    else:
        print(f"  ⚠ 无法登录在线后端，将仅保存本地")

    # 生成章节
    results = []
    failed = []

    for chapter_num in range(61, 81):
        try:
            content = generate_chapter(chapter_num, context, token)
            if content:
                results.append(chapter_num)
            else:
                failed.append(chapter_num)
                print(f"  ❌ 第{chapter_num}章生成失败，继续下一章...")

            # 章节之间短暂暂停，避免 API 限流
            if chapter_num < 80:
                print(f"  ⏸  暂停3秒...")
                time.sleep(3)

        except KeyboardInterrupt:
            print(f"\n⚠ 用户中断! 已完成: {results}, 未完成: {list(range(chapter_num, 81))}")
            break
        except Exception as e:
            print(f"  ❌ 第{chapter_num}章异常: {e}")
            failed.append(chapter_num)

    # 总结
    print(f"\n{'='*60}")
    print(f"📊 生成完毕!")
    print(f"  成功: {len(results)} 章 - {results}")
    print(f"  失败: {len(failed)} 章 - {failed}")
    print(f"  本地路径: {CHAPTERS_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
