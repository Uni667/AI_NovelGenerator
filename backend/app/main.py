import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import init_db
from backend.app.routes import config, projects, chapters, files, knowledge, generation, characters, platform_tools, auth, character_relationships, character_conflicts, character_appearances

# 统一日志配置（整个应用只在此处配置一次）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://ai-novel-generator-topaz.vercel.app,https://ai-novel-generator.vercel.app,https://frontend-chi-one-84.vercel.app"
).split(",")

app = FastAPI(title="AI 小说生成器 API", version="1.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router)
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


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "AI 小说生成器"}
