# -*- coding: utf-8 -*-
"""监控批量生成，每5分钟报告进度，自动下载完成的章节"""
import requests, json, time, os, sys

BACKEND = "https://ai-novel-backend-production.up.railway.app"
PROJECT = "ef1de677-1a9a-4f28-9516-554e5a53838a"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiODlmNmQzZTctZGY3MC00MTVmLTgxOTQtMjZmNjliZDk4NDg0IiwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc4MDQwMTQ0OCwiZXhwIjoxNzgwNDA4NjQ4fQ.F_J_4pPoquAIr5YSBJ36WH3xj0Z7q9Fs-hyYyA0nWRo"
LOCAL = r"C:\Users\Lenovo\Desktop\万界仙帝\章节"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

START, END = 62, 80
os.makedirs(LOCAL, exist_ok=True)

def downloaded_chapters():
    result = set()
    for f in os.listdir(LOCAL):
        if f.startswith("chapter_") and f.endswith(".txt"):
            try:
                result.add(int(f.replace("chapter_","").replace(".txt","")))
            except: pass
    return result

downloaded = downloaded_chapters()
print(f"Monitor: Ch {START}-{END}, already have: {sorted(downloaded)}")
sys.stdout.flush()

last_status = ""
next_report = time.time() + 300  # 5 min

while len(downloaded) < (END - START + 1) + 1:
    try:
        # Download completed chapters
        for ch in range(START, END + 1):
            if ch in downloaded:
                continue
            try:
                resp = requests.get(f"{BACKEND}/api/v1/projects/{PROJECT}/chapters/{ch}", headers=HEADERS, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("content","")
                    if content and len(content.strip()) > 500:
                        fpath = os.path.join(LOCAL, f"chapter_{ch:04d}.txt")
                        with open(fpath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        downloaded.add(ch)
                        print(f"[{time.strftime('%H:%M:%S')}] Ch {ch}: {len(content)} chars saved")
                        sys.stdout.flush()
            except: pass

        # Check task
        try:
            resp = requests.get(f"{BACKEND}/api/v1/projects/{PROJECT}/generate/tasks", headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                tasks = resp.json()
                active = [t for t in tasks if t.get("status") in ("running","pending")]
                if active:
                    t = active[0]
                    s = f"[{t.get('status')}] {t.get('current_step','')}: {t.get('message','')[:80]}"
                    if s != last_status:
                        print(f"[{time.strftime('%H:%M:%S')}] Task: {s}")
                        sys.stdout.flush()
                        last_status = s
        except: pass

        # Progress report every 5 min
        if time.time() >= next_report:
            remaining = [ch for ch in range(START, END+1) if ch not in downloaded]
            done_count = len([ch for ch in range(61, END+1) if (ch == 61) or (ch in downloaded)])
            total_count = END - 60
            print(f"\n--- Progress: {done_count}/{total_count} chapters ---")
            print(f"  Done: {sorted(downloaded)}")
            print(f"  Remaining: {remaining}")
            sys.stdout.flush()
            next_report = time.time() + 300

    except KeyboardInterrupt:
        break

    time.sleep(15)

# Final report
remaining = [ch for ch in range(START, END+1) if ch not in downloaded]
print(f"\n=== FINAL ===")
print(f"  Done ({len(downloaded)}): {sorted(downloaded)}")
print(f"  Missing: {remaining}")
print(f"  Files: {LOCAL}")
