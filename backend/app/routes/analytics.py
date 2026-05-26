# -*- coding: utf-8 -*-
"""
API endpoints for API call costs, latency, success rate and models usage statistics.
"""
import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.services import project_service

router = APIRouter(tags=["调用分析"])


def estimate_cost(provider: str, model: str, input_chars: int, output_chars: int) -> float:
    """
    Estimate the API cost in CNY based on characters count.
    As character counts are rough approximations of tokens, we set reasonable cost factors.
    Rates are given in CNY per 1,000,000 characters.
    """
    model_lower = model.lower() if model else ""
    prov_lower = provider.lower() if provider else ""
    
    # Defaults (approx Qwen2.5 / DeepSeek V3 pricing)
    # Input: 1.0 CNY / Million chars, Output: 2.0 CNY / Million chars
    input_rate = 1.0 / 1_000_000
    output_rate = 2.0 / 1_000_000
    
    if "reasoner" in model_lower or "r1" in model_lower:
        # DeepSeek R1 / Reasoner pricing (Input: 2 CNY / Million chars, Output: 8 CNY / Million chars)
        input_rate = 2.0 / 1_000_000
        output_rate = 8.0 / 1_000_000
    elif "gpt-4" in model_lower:
        # GPT-4 Class (Input: 30 CNY / Million chars, Output: 90 CNY / Million chars)
        input_rate = 30.0 / 1_000_000
        output_rate = 90.0 / 1_000_000
    elif "claude-3" in model_lower:
        # Claude 3 Class (Input: 20 CNY / Million chars, Output: 60 CNY / Million chars)
        input_rate = 20.0 / 1_000_000
        output_rate = 60.0 / 1_000_000
    elif "qwen" in model_lower or "llama" in model_lower or "deepseek" in model_lower:
        # Standard cheap models
        input_rate = 1.0 / 1_000_000
        output_rate = 2.0 / 1_000_000
        
    return (input_chars or 0) * input_rate + (output_chars or 0) * output_rate


@router.get("/api/v1/projects/{project_id}/analytics")
def get_project_analytics(project_id: str, request: Request):
    """
    Query and aggregate the model invocation logs for a project to provide cost,
    performance, and failure statistics.
    """
    user_id = get_current_user(request)
    # Verify project exists and user owns it
    project_service.get_project(project_id, user_id)
    
    with get_db() as conn:
        # Fetch all invocations for the project to calculate accurate statistics
        # (aggregate on Python side to compute custom costs accurately)
        rows = conn.execute(
            """
            SELECT provider, model, purpose, input_chars, output_chars, 
                   latency_ms, success, error_code, error_message, created_at 
            FROM model_invocation_log 
            WHERE project_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (project_id, user_id)
        ).fetchall()
        
    # Standardize data into dictionary format
    logs = []
    for r in rows:
        logs.append({
            "provider": r[0] or "unknown",
            "model": r[1] or "unknown",
            "purpose": r[2] or "general",
            "input_chars": r[3] or 0,
            "output_chars": r[4] or 0,
            "latency_ms": r[5] or 0,
            "success": bool(r[6]),
            "error_code": r[7] or "",
            "error_message": r[8] or "",
            "created_at": r[9],
            "cost": estimate_cost(r[0], r[1], r[3], r[4])
        })
        
    # Aggregate data
    total_calls = len(logs)
    success_calls = sum(1 for log in logs if log["success"])
    success_rate = (success_calls / total_calls) if total_calls > 0 else 0.0
    avg_latency = (sum(log["latency_ms"] for log in logs) / total_calls) if total_calls > 0 else 0.0
    total_input = sum(log["input_chars"] for log in logs)
    total_output = sum(log["output_chars"] for log in logs)
    total_cost = sum(log["cost"] for log in logs)
    
    # 1. Group by model
    model_groups = {}
    for log in logs:
        key = (log["provider"], log["model"])
        if key not in model_groups:
            model_groups[key] = []
        model_groups[key].append(log)
        
    by_model = []
    for (provider, model), group in model_groups.items():
        cnt = len(group)
        sc = sum(1 for g in group if g["success"])
        by_model.append({
            "provider": provider,
            "model": model,
            "count": cnt,
            "success_rate": sc / cnt if cnt > 0 else 0.0,
            "estimated_cost_cny": sum(g["cost"] for g in group),
            "input_chars": sum(g["input_chars"] for g in group),
            "output_chars": sum(g["output_chars"] for g in group),
            "avg_latency_ms": sum(g["latency_ms"] for g in group) / cnt if cnt > 0 else 0.0
        })
        
    # Sort by cost descending, then count descending
    by_model.sort(key=lambda x: (x["estimated_cost_cny"], x["count"]), reverse=True)
    
    # 2. Group by purpose
    purpose_groups = {}
    for log in logs:
        p = log["purpose"]
        if p not in purpose_groups:
            purpose_groups[p] = []
        purpose_groups[p].append(log)
        
    by_purpose = []
    for purpose, group in purpose_groups.items():
        cnt = len(group)
        sc = sum(1 for g in group if g["success"])
        by_purpose.append({
            "purpose": purpose,
            "count": cnt,
            "success_rate": sc / cnt if cnt > 0 else 0.0,
            "estimated_cost_cny": sum(g["cost"] for g in group),
            "avg_latency_ms": sum(g["latency_ms"] for g in group) / cnt if cnt > 0 else 0.0
        })
    by_purpose.sort(key=lambda x: x["count"], reverse=True)
    
    # 3. Group by provider
    provider_groups = {}
    for log in logs:
        prov = log["provider"]
        if prov not in provider_groups:
            provider_groups[prov] = []
        provider_groups[prov].append(log)
        
    by_provider = []
    for provider, group in provider_groups.items():
        cnt = len(group)
        sc = sum(1 for g in group if g["success"])
        by_provider.append({
            "provider": provider,
            "count": cnt,
            "success_rate": sc / cnt if cnt > 0 else 0.0,
            "estimated_cost_cny": sum(g["cost"] for g in group),
            "avg_latency_ms": sum(g["latency_ms"] for g in group) / cnt if cnt > 0 else 0.0
        })
    by_provider.sort(key=lambda x: x["count"], reverse=True)
    
    # 4. Errors
    error_groups = {}
    for log in logs:
        if not log["success"]:
            err = log["error_code"] or "UNKNOWN"
            if err not in error_groups:
                error_groups[err] = []
            error_groups[err].append(log)
            
    errors = []
    for err, group in error_groups.items():
        errors.append({
            "error_code": err,
            "count": len(group),
            "last_message": group[-1]["error_message"]
        })
    errors.sort(key=lambda x: x["count"], reverse=True)
    
    # 5. Daily trend (last 30 days)
    daily_groups = {}
    for log in logs:
        # Extract YYYY-MM-DD from created_at
        date_str = log["created_at"][:10] if log["created_at"] else "unknown"
        if date_str not in daily_groups:
            daily_groups[date_str] = []
        daily_groups[date_str].append(log)
        
    # Sort dates
    sorted_dates = sorted(daily_groups.keys())
    
    # Limit to last 30 days if there are too many
    if len(sorted_dates) > 30:
        sorted_dates = sorted_dates[-30:]
        
    daily_trend = []
    for date_str in sorted_dates:
        group = daily_groups[date_str]
        cnt = len(group)
        sc = sum(1 for g in group if g["success"])
        daily_trend.append({
            "date": date_str,
            "count": cnt,
            "success_rate": sc / cnt if cnt > 0 else 0.0,
            "estimated_cost_cny": sum(g["cost"] for g in group),
            "input_chars": sum(g["input_chars"] for g in group),
            "output_chars": sum(g["output_chars"] for g in group)
        })
        
    return {
        "summary": {
            "total_calls": total_calls,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
            "total_input_chars": total_input,
            "total_output_chars": total_output,
            "estimated_cost_cny": total_cost
        },
        "by_model": by_model,
        "by_purpose": by_purpose,
        "by_provider": by_provider,
        "errors": errors,
        "daily_trend": daily_trend
    }
