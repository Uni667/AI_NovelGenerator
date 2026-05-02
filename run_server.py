#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI 小说生成器 Web 版 - 一键启动脚本"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  AI 小说生成器 Web 版")
    print("  API 文档: http://localhost:8001/docs")
    print("  前端地址: http://localhost:3000")
    print("=" * 50)
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        timeout_keep_alive=300,
        log_level="info"
    )
