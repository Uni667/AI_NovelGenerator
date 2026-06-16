# -*- coding: utf-8 -*-
"""
通过在线后端 API 生成万界仙帝第61-80章
使用 SSE 流式接口触发生成，轮询任务状态，生成后下载到本地
"""
import requests
import json
import time
import os
import sys

# 配置
BACKEND_URL = "https://ai-novel-backend-production.up.railway.app"
PROJECT_ID = "ef1de677-1a9a-4f28-9516-554e5a53838a"
USERNAME = "wanjie_xiandi"
PASSWORD = "xk9mF2#pLq7vBn3"

# 本地路径
LOCAL_CHAPTERS_DIR = r"C:\Users\Lenovo\Desktop\万界仙帝\章节"

# 全局 token
TOKEN = None

def login():
    """登录获取令牌"""
    global TOKEN
    resp = requests.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=15
    )
    if resp.status_code == 200:
        data = resp.json()
        TOKEN = data["token"]
        print(f"✓ 登录成功 (用户: {data['username']})")
        return True
    print(f"✗ 登录失败: {resp.status_code}")
    return False

def headers():
    return {"Authorization": f"Bearer {TOKEN}"}

def check_project():
    """检查项目状态"""
    resp = requests.get(f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}", headers=headers(), timeout=15)
    if resp.status_code == 200:
        p = resp.json()
        print(f"✓ 项目: {p['name']} (状态: {p['status']})")
        return p
    print(f"✗ 获取项目失败: {resp.status_code}")
    return None

def trigger_batch_generation(start_chapter, count, enable_brainstorming=False):
    """
    触发批量章节生成 (SSE 流式接口)
    由于是 SSE，我们启动后立即断开，让任务在后台运行
    """
    url = f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/generate/chapters"
    params = {
        "start_chapter": start_chapter,
        "count": count,
        "enable_brainstorming": str(enable_brainstorming).lower()
    }

    print(f"  触发批量生成: Ch {start_chapter}-{start_chapter + count - 1}")

    try:
        # 使用 stream=True 来捕获 SSE 事件
        resp = requests.post(url, headers=headers(), params=params, stream=True, timeout=30)

        # 读取前几个 SSE 事件获取 task_id
        task_id = None
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    if "task_id" in data:
                        task_id = data["task_id"]
                        print(f"  ✓ 任务已启动: {task_id}")
                        break
                    # 打印进度
                    step = data.get("step", "")
                    status = data.get("status", "")
                    msg = data.get("message", "")
                    if msg:
                        print(f"  [{step}/{status}] {msg[:80]}")
                except:
                    pass

        resp.close()
        return task_id
    except requests.exceptions.Timeout:
        print(f"  ⚠ 请求超时（任务可能已在后台启动）")
        return None
    except Exception as e:
        print(f"  ✗ 触发失败: {e}")
        return None

def get_active_task():
    """获取当前活跃的生成任务"""
    resp = requests.get(
        f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/generate/tasks",
        headers=headers(), timeout=15
    )
    if resp.status_code == 200:
        tasks = resp.json()
        for task in tasks:
            if task.get("status") in ("running", "pending"):
                return task
        # 返回最新的任务
        if tasks:
            return tasks[0]
    return None

def poll_task(task_id, timeout_minutes=30):
    """轮询任务直到完成"""
    print(f"  ⏳ 等待任务完成 (最多 {timeout_minutes} 分钟)...")
    start = time.time()
    timeout = timeout_minutes * 60

    last_msg = ""
    while time.time() - start < timeout:
        resp = requests.get(
            f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/generate/tasks/{task_id}",
            headers=headers(), timeout=15
        )
        if resp.status_code == 200:
            task = resp.json()
            status = task.get("status", "")
            msg = task.get("message", "")
            step = task.get("current_step", "")

            # 打印进度（避免重复）
            progress = f"  [{status}] {step}: {msg[:60]}"
            if progress != last_msg:
                print(progress)
                last_msg = progress

            if status in ("done", "failed", "cancelled"):
                print(f"  任务结束: {status}")
                if msg:
                    print(f"  消息: {msg}")
                return task
        else:
            print(f"  ⚠ 查询任务失败: {resp.status_code}")

        time.sleep(15)  # 每15秒检查一次

    print(f"  ⚠ 超时!")
    return None

def wait_for_chapter(chapter_num, timeout_minutes=30):
    """等待指定章节出现在列表中"""
    print(f"  ⏳ 等待第 {chapter_num} 章生成...")
    start = time.time()
    timeout = timeout_minutes * 60

    while time.time() - start < timeout:
        resp = requests.get(
            f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/chapters/{chapter_num}",
            headers=headers(), timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")
            if content and len(content.strip()) > 500:
                print(f"  ✓ 第 {chapter_num} 章已生成 ({len(content)} 字符)")
                return content
            elif content.strip():
                print(f"  ⏳ 第 {chapter_num} 章内容较短 ({len(content)} 字符)，继续等待...")

        time.sleep(10)

    print(f"  ⚠ 超时! 第 {chapter_num} 章未完成")
    return None

def download_chapter(chapter_num):
    """从服务器下载章节"""
    resp = requests.get(
        f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/chapters/{chapter_num}",
        headers=headers(), timeout=15
    )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("content", "")
    return None

def save_local(chapter_num, content):
    """保存到本地"""
    filename = f"chapter_{chapter_num:04d}.txt"
    filepath = os.path.join(LOCAL_CHAPTERS_DIR, filename)
    os.makedirs(LOCAL_CHAPTERS_DIR, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ 已保存: {filepath}")
    return filepath

def generate_chapter_single(chapter_num, enable_brainstorming=False):
    """生成单个章节（通过在线 API）"""
    print(f"\n{'─'*50}")
    print(f"📝 第 {chapter_num} 章")

    # 触发单章生成
    url = f"{BACKEND_URL}/api/v1/projects/{PROJECT_ID}/generate/chapter/{chapter_num}"
    params = {}
    if enable_brainstorming:
        params["enable_brainstorming"] = "true"

    task_id = None
    try:
        resp = requests.post(url, headers=headers(), params=params, stream=True, timeout=30)
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    if "task_id" in data:
                        task_id = data["task_id"]
                        print(f"  任务ID: {task_id}")
                    msg = data.get("message", "")
                    if msg and "draft" in str(data.get("step", "")):
                        print(f"  {msg[:100]}")
                except:
                    pass
        resp.close()
    except Exception as e:
        print(f"  ⚠ 请求异常: {e}")

    if not task_id:
        # 尝试从活跃任务列表获取
        task = get_active_task()
        if task:
            task_id = task.get("task_id")

    if task_id:
        # 轮询任务
        result = poll_task(task_id, timeout_minutes=15)
        if result and result.get("status") == "done":
            content = download_chapter(chapter_num)
            if content:
                save_local(chapter_num, content)
                return content
    else:
        # 直接等待章节出现
        print(f"  无法获取任务ID，直接等待章节生成...")
        return wait_for_chapter(chapter_num, timeout_minutes=15)

    return None

def main():
    print("╔══════════════════════════════════════╗")
    print("║  万界仙帝 Ch61-80 在线API生成      ║")
    print("╚══════════════════════════════════════╝")

    # 登录
    if not login():
        print("无法登录，退出。")
        return

    # 检查项目
    if not check_project():
        return

    # 确保本地目录存在
    os.makedirs(LOCAL_CHAPTERS_DIR, exist_ok=True)

    # 生成章节 61-80
    results = []
    failed = []

    START = 61
    END = 80

    for chapter_num in range(START, END + 1):
        try:
            content = generate_chapter_single(chapter_num, enable_brainstorming=False)
            if content and len(content.strip()) > 500:
                results.append(chapter_num)
                print(f"  ✅ 第{chapter_num}章完成 ({len(content)} 字符)")
            else:
                failed.append(chapter_num)
                print(f"  ❌ 第{chapter_num}章生成失败或内容过短")

            # 章节间短暂暂停
            if chapter_num < END:
                time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n⚠ 用户中断! 已完成: {results}")
            break
        except Exception as e:
            print(f"  ❌ 第{chapter_num}章异常: {e}")
            failed.append(chapter_num)

    # 总结
    print(f"\n{'='*60}")
    print(f"📊 生成完毕!")
    print(f"  成功: {len(results)} 章 - Ch {min(results) if results else 'N/A'}-{max(results) if results else 'N/A'}")
    print(f"  失败: {len(failed)} 章 - {failed}")
    print(f"  本地路径: {LOCAL_CHAPTERS_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
