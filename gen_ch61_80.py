# -*- coding: utf-8 -*-
"""
万界仙帝 Ch61-80 批量生成脚本
策略：优先使用在线 API，如果失败则本地 DeepSeek 直接生成
生成后自动同步到本地文件夹：C:\Users\Lenovo\Desktop\万界仙帝\章节\
"""
import os
import sys
import json
import time
import re
import requests
from datetime import datetime

# 绕过 Windows 系统代理，防止 Clash 代理失效/关闭时导致 requests 库请求挂起
os.environ['NO_PROXY'] = '*'

# ============================================================
# 配置
# ============================================================
BACKEND_URL = "https://ai-novel-backend-production.up.railway.app"
PROJECT_ID = "ef1de677-1a9a-4f28-9516-554e5a53838a"
USERNAME = "wanjie_xiandi"
PASSWORD = "xk9mF2#pLq7vBn3"

# DeepSeek API (备用)
DEEPSEEK_KEY = "sk-f19e0657b95c40cda2d760b49bfc30c2"
DEEPSEEK_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# 本地路径
LOCAL_CHAPTERS = r"C:\Users\Lenovo\Desktop\万界仙帝\章节"
LOCAL_SETTINGS = r"C:\Users\Lenovo\Desktop\万界仙帝\设定"

# 写作要求
WRITING_RULES = """
【铁律 - 必须严格遵守】
1. 角色出场自然：通过事件/对话/环境引入，禁止"突然出现+旁白介绍"
2. 文笔精炼：减少直白叙述，用细节和行动展示，对话有角色辨识度
3. 暗线长铺垫：重要伏笔跨多章展开，不要本章引出下章就揭晓
4. 人物通过事件深化：通过选择和行动展现性格，关键配角要有记忆点
5. 每章3000-5000字，以倒计时天数开头
"""

TOKEN = None
CHAPTERS_DIR = None
SETTINGS_DIR = None


# ============================================================
# 工具函数
# ============================================================
def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return ""

def login():
    global TOKEN
    try:
        resp = requests.post(f"{BACKEND_URL}/api/v1/auth/login",
            json={"username": USERNAME, "password": PASSWORD}, timeout=15)
        if resp.status_code == 200:
            TOKEN = resp.json()["token"]
            return True
    except:
        pass
    return False

def call_deepseek(system_prompt, user_prompt, temperature=0.7, max_tokens=8192):
    """直接调用 DeepSeek API"""
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": temperature, "max_tokens": max_tokens, "stream": False
    }
    for attempt in range(3):
        try:
            resp = requests.post(f"{DEEPSEEK_BASE}/chat/completions", headers=headers, json=payload, timeout=300)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            print(f"  ⚠ DeepSeek API error (attempt {attempt+1}): {resp.status_code} {resp.text[:150]}")
            if attempt < 2: time.sleep(2 ** attempt * 5)
        except Exception as e:
            print(f"  ⚠ DeepSeek request error (attempt {attempt+1}): {e}")
            if attempt < 2: time.sleep(2 ** attempt * 5)
    return None

def save_local(chapter_num, content):
    os.makedirs(LOCAL_CHAPTERS, exist_ok=True)
    filepath = os.path.join(LOCAL_CHAPTERS, f"chapter_{chapter_num:04d}.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  💾 {filepath}")
    return True

def upload_to_server(chapter_num, content):
    if not TOKEN and not login():
        return False
    try:
        resp = requests.put(
            f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/chapters/{chapter_num}",
            json={"content": content, "status": "draft"},
            headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30)
        if resp.status_code == 200:
            print(f"  ☁️ 已上传服务器")
            return True
        print(f"  ⚠ 上传失败: {resp.status_code}")
    except Exception as e:
        print(f"  ⚠ 上传异常: {e}")
    return False

def get_chapter_blueprint(chapter_num):
    """提取章节蓝图信息"""
    text = read_file(os.path.join(LOCAL_SETTINGS, "Novel_directory.txt"))
    if not text:
        return f"第{chapter_num}章", ""

    # 用正则匹配
    pattern = rf'\*\*第{chapter_num}章 - ([^*]+)\*\*\n(.*?)(?=\n\*\*第\d+章|\n# |\Z)'
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # 备用：逐行匹配
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if f'第{chapter_num}章' in line and '**' in line:
            ctx = []
            for j in range(i, min(i+15, len(lines))):
                ctx.append(lines[j])
                if j > i and '**第' in lines[j] and '章' in lines[j]:
                    break
            return line.strip(), '\n'.join(ctx)
    return f"第{chapter_num}章", ""

def get_recent_chapters(n=5):
    """获取最近N章作为上下文"""
    parts = []
    for i in range(60 - n + 1, 61):
        path = os.path.join(LOCAL_CHAPTERS, f"chapter_{i:04d}.txt")
        content = read_file(path)
        if content:
            if len(content) > 1000:
                parts.append(f"【第{i}章】\n{content[:400]}\n...\n{content[-300:]}")
            else:
                parts.append(f"【第{i}章】\n{content[:800]}")
    return "\n\n".join(parts)

def load_context():
    """加载全局上下文"""
    ctx = {}
    for name in ["全局摘要.txt", "核心摘要.txt", "角色年卡.txt"]:
        content = read_file(os.path.join(LOCAL_SETTINGS, name))
        ctx[name.replace('.txt','')] = content[:2500] if content else ""
    return ctx


# ============================================================
# 核心：构建提示词 & 生成
# ============================================================
def build_prompt(chapter_num, title, blueprint, ctx):
    """构建一章的提示词"""
    recent = get_recent_chapters(5)

    system = f"""你是一位资深网络小说作家，正在创作仙侠小说《万界仙帝》。主角林尘，女主苏月（帝妃转世）。

{WRITING_RULES}

【故事核心设定】
- 林尘：被家族抛弃后获得不朽皇帝种子传承，已突破帝境。老乞丐（七大战将之一）在第58章牺牲。
- 苏月：帝妃转世，体内有法器碎片，觉醒了部分前世记忆。第60章她决定用法器碎片引爆东极帝君的帝咒。
- 东极帝君：万年前背叛不朽皇帝的四方帝君之首，对帝妃有病态执念。
- 当前时间：百日倒计时第83-90天。东极帝君的帝咒即将在第85天发作。
- 南极帝君：两面派，表面合作实则伺机夺取传承。
- 北极帝君：尚未表态，暗中观察。
- 西极帝君：已被林尘斩杀(第62章)。

【核心暗线（持续推进但不过早揭露）】
1. 不朽皇帝的种子是双刃剑 - 既是传承也是陷阱
2. 苏月前世下毒真相 - 皇帝的自杀式布局，她只是执行者
3. 东极帝君对帝妃的万年执念 - 他的一切行动都为了让她"回来"
4. 母亲被囚禁在时空裂隙 - 林尘尚未得知全部真相
5. 四方帝君的帝咒连锁 - 不朽皇帝临死反噬，西极帝君陨落会触发连锁

【文风要求】
- 冷峻克制，有画面感
- 战斗场景要有具体动作，不写"一拳打飞"
- 情感场景通过细节传达，不直接写"他很伤心"
- 对话有角色辨识度：林尘冷峻果断，苏月温柔坚韧，东极偏执疯狂
- 叙事节奏紧凑，每章要有推进感
- 禁止灌水、禁止重复套路、禁止角色千人一面
"""

    user = f"""请创作《万界仙帝》第{chapter_num}章。

【本章蓝图】
标题：{title}
{blueprint}

【最近章节上下文】
{recent}

【全局剧情】
{ctx.get('全局摘要','')[:1500]}

【角色状态】
{ctx.get('角色年卡','')[:1500]}

创作要求：
1. 以"第{chapter_num}天。"或对应天数开头
2. 严格按蓝图的核心事件来写
3. 3000-5000字
4. 暗线推进但不揭晓，本章埋的伏笔至少延后3-5章回收
5. 不要突然引入新角色并旁白介绍身份

请直接开始创作正文，输出格式：
# 第{chapter_num}章 {title}

（正文内容）"""

    return system, user


def generate_chapter(chapter_num, ctx):
    """生成单个章节"""
    print(f"\n{'─'*55}")
    print(f"📝 第 {chapter_num} 章")

    title, blueprint = get_chapter_blueprint(chapter_num)
    print(f"   《{title}》")

    system, user = build_prompt(chapter_num, title, blueprint, ctx)

    print(f"   ⏳ 调用 DeepSeek API...")
    t0 = time.time()
    content = call_deepseek(system, user)
    elapsed = time.time() - t0

    if not content:
        print(f"   ❌ 生成失败!")
        return None

    # 确保有标题
    if not content.startswith("#"):
        content = f"# 第{chapter_num}章 {title}\n\n{content}"

    wc = len(content)
    print(f"   ✅ 完成! {elapsed:.0f}s, {wc}字")

    # 保存
    save_local(chapter_num, content)
    upload_to_server(chapter_num, content)

    return content


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 55)
    print("  万界仙帝 · 第61-80章 · 批量生成")
    print("=" * 55)

    # 初始化
    os.makedirs(LOCAL_CHAPTERS, exist_ok=True)

    # 加载上下文
    print("\n📚 加载上下文...")
    ctx = load_context()
    for k, v in ctx.items():
        print(f"   {k}: {len(v)}字")

    # 尝试登录在线后端
    if login():
        print("🔑 已登录在线后端")
    else:
        print("⚠️ 无法登录在线后端，将仅保存本地")

    # 生成
    results, failed = [], []

    for ch in range(61, 81):
        try:
            content = generate_chapter(ch, ctx)
            if content and len(content) > 500:
                results.append(ch)
            else:
                failed.append(ch)
            if ch < 80:
                time.sleep(3)  # API rate limit
        except KeyboardInterrupt:
            print(f"\n⚠️ 用户中断! 已完成: {results}")
            break
        except Exception as e:
            print(f"   ❌ 异常: {e}")
            failed.append(ch)

    # 总结
    print(f"\n{'='*55}")
    print(f"📊 完成!")
    print(f"   成功: {len(results)}章 ({min(results) if results else 'N/A'}-{max(results) if results else 'N/A'})")
    print(f"   失败: {len(failed)}章 {failed if failed else ''}")
    print(f"   本地: {LOCAL_CHAPTERS}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
