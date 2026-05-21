#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One-command backend launcher for the AI Novel Generator."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("  AI Novel Generator Web")
    print("  API docs: http://localhost:8001/docs")
    print("  Frontend: http://localhost:3000")
    print("=" * 50)
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        timeout_keep_alive=300,
        log_level="info",
    )
