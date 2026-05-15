import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.database import init_db
from backend.app.routes import auth, chapters, character_appearances, character_conflicts, character_relationships, characters, files, generation, knowledge, platform_tools, projects, user_api_config
from backend.app.rate_limiter import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# 统一日志配置（整个应用只在此处配置一次）
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(log_dir, exist_ok=True)

log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 控制台输出
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# 文件输出（轮转：每个文件 10MB，保留 5 个备份）
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler],
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app = FastAPI(title="AI 小说生成器 API", version="1.0", docs_url="/docs")

# 注册速率限制错误处理器
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# 应用速率限制中间件
app.state.limiter = limiter

app.include_router(projects.router)
app.include_router(chapters.router)
app.include_router(files.router)
app.include_router(knowledge.router)
app.include_router(generation.router)
app.include_router(characters.router)
app.include_router(platform_tools.router)
app.include_router(auth.router)
app.include_router(character_relationships.router)
app.include_router(character_conflicts.router)
app.include_router(character_appearances.router)
app.include_router(user_api_config.router)


@app.on_event("startup")
def startup():
    init_db()
    from novel_generator.task_manager import load_tasks_from_db
    load_tasks_from_db()


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "AI 小说生成器"}
