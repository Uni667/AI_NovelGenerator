# -*- coding: utf-8 -*-
"""Download chapters 74-80 as they complete"""
import requests, os, time

# 绕过 Windows 系统代理，防止 Clash 代理失效/关闭时导致 requests 库请求挂起
os.environ['NO_PROXY'] = '*'

BACKEND = 'https://ai-novel-backend-production.up.railway.app'
PROJECT = 'ef1de677-1a9a-4f28-9516-554e5a53838a'
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiODlmNmQzZTctZGY3MC00MTVmLTgxOTQtMjZmNjliZDk4NDg0IiwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc4MDQwMTQ0OCwiZXhwIjoxNzgwNDA4NjQ4fQ.F_J_4pPoquAIr5YSBJ36WH3xj0Z7q9Fs-hyYyA0nWRo'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}
LOCAL = r'C:\Users\Lenovo\Desktop\万界仙帝\章节'

os.makedirs(LOCAL, exist_ok=True)
targets = set(range(74, 81))

print(f'Waiting for chapters: {sorted(targets)}')

start = time.time()
while targets and time.time() - start < 1200:
    for ch in list(targets):
        try:
            resp = requests.get(f'{BACKEND}/api/v1/projects/{PROJECT}/chapters/{ch}', headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                content = d.get('content','')
                if content and len(content.strip()) > 500:
                    fpath = os.path.join(LOCAL, f'chapter_{ch:04d}.txt')
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    targets.discard(ch)
                    print(f'[{time.strftime("%H:%M:%S")}] Ch {ch}: {len(content)} chars')
        except: pass
    if targets:
        time.sleep(15)

if targets:
    print(f'Timeout! Missing: {sorted(targets)}')
else:
    print('All chapters 74-80 downloaded!')
