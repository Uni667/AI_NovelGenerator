# Project Rules for AI Novel Generator

This file contains general guidelines and constraints for developers and AI agents working on this codebase.

## Codebase Architecture
- **Backend**: FastAPI + SQLite. Database models are located in `backend/app/database.py`. Services are in `backend/app/services/`.
- **Frontend**: Next.js App Router (React 19) + TypeScript + Tailwind CSS.
- **Novel Generation**: Python-based pipeline under `novel_generator/`.

## General Constraints
1. **Secret Management**:
   - Never commit actual API keys to git.
   - Do not modify `.env` files with production values. Use `.env.example` as a template.
2. **Database Schema Changes**:
   - Any schema changes must be accompanied by appropriate migrations.
   - Keep migrations consistent with test setups.
3. **Local Library Security**:
   - All local file accesses must pass validation in `LocalFileGuard` to prevent sandbox escapes.
   - Always honor `ALLOW_LOCAL_FILE_ACCESS=false` configuration to allow complete feature disablement.
4. **LLM RAG Best Practice**:
   - Never inject raw, full novel chapters into prompts. Always extract abstract structural/style metadata rules (Essence) and use those.

## Testing & Quality Control
- **Backend Tests**: Run `pytest backend/tests` to verify changes.
- **Frontend Linting & Build**: Always run `npm run typecheck` and `npm run build` inside the `frontend` folder before pushing.
