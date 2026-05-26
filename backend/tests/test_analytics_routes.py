# -*- coding: utf-8 -*-
import pytest
import datetime
from backend.app.database import get_db


class TestAnalyticsRoutes:
    """测试 API 调用分析统计接口 (P2)。"""

    def test_analytics_empty(self, client, auth_headers, test_project):
        """当没有任何调用日志时，接口应返回零初始值及空的分组。"""
        response = client.get(
            f"/api/v1/projects/{test_project['id']}/analytics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # 验证默认 summary
        summary = data["summary"]
        assert summary["total_calls"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["avg_latency_ms"] == 0.0
        assert summary["total_input_chars"] == 0
        assert summary["total_output_chars"] == 0
        assert summary["estimated_cost_cny"] == 0.0
        
        # 验证分组列表为空
        assert len(data["by_model"]) == 0
        assert len(data["by_purpose"]) == 0
        assert len(data["by_provider"]) == 0
        assert len(data["errors"]) == 0
        assert len(data["daily_trend"]) == 0

    def test_analytics_aggregation(self, client, auth_headers, test_project):
        """写入多条模拟调用日志，测试聚合与开销估算逻辑是否准确。"""
        project_id = test_project["id"]
        
        # 获取用户 ID，需要读取一个已注册的用户
        # 通过 client headers 中的 token 对应的用户，为了简单，我们可以先获取 db
        with get_db() as conn:
            # 找到项目关联的用户 ID
            row = conn.execute("SELECT user_id FROM project WHERE id = ?", (project_id,)).fetchone()
            user_id = row[0]
            
            # 清空已有日志（防止脏数据干扰）
            conn.execute("DELETE FROM model_invocation_log WHERE project_id = ?", (project_id,))
            
            # 插入模拟调用日志
            now = datetime.datetime.now()
            day1 = (now - datetime.timedelta(days=1)).isoformat()
            day2 = now.isoformat()
            
            logs_to_insert = [
                # 成功的 R1 模型调用 (day1)
                ("log1", user_id, project_id, "task1", "cred1", "prof1", "deepseek", "deepseek-reasoner", "draft", 1000, 2000, 5000, 1, None, None, day1),
                # 成功的 chat 模型调用 (day2)
                ("log2", user_id, project_id, "task2", "cred1", "prof1", "siliconflow", "deepseek-chat", "brainstorm", 500, 800, 1500, 1, None, None, day2),
                # 失败的 chat 模型调用 (day2)
                ("log3", user_id, project_id, "task2", "cred1", "prof1", "siliconflow", "deepseek-chat", "brainstorm", 400, 0, 800, 0, "rate_limit", "Rate limit exceeded", day2),
            ]
            
            for item in logs_to_insert:
                conn.execute(
                    """
                    INSERT INTO model_invocation_log 
                    (id, user_id, project_id, task_id, api_credential_id, model_profile_id,
                     provider, model, purpose, input_chars, output_chars, latency_ms,
                     success, error_code, error_message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    item
                )
                
        # 请求接口
        response = client.get(
            f"/api/v1/projects/{project_id}/analytics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # 1. 验证汇总数据 (Summary)
        summary = data["summary"]
        assert summary["total_calls"] == 3
        # 3 次调用，2 次成功 -> 2/3 = 0.6666...
        assert abs(summary["success_rate"] - (2.0 / 3.0)) < 1e-4
        # 平均延时: (5000 + 1500 + 800) / 3 = 2433.333...
        assert abs(summary["avg_latency_ms"] - 2433.3333) < 1.0
        assert summary["total_input_chars"] == 1000 + 500 + 400
        assert summary["total_output_chars"] == 2000 + 800 + 0
        
        # 验证估算开销:
        # log1: deepseek-reasoner (R1) -> input: 1000 * (2/1M) = 0.002, output: 2000 * (8/1M) = 0.016 -> 0.018 CNY
        # log2: siliconflow deepseek-chat -> input: 500 * (1/1M) = 0.0005, output: 800 * (2/1M) = 0.0016 -> 0.0021 CNY
        # log3: siliconflow deepseek-chat -> input: 400 * (1/1M) = 0.0004, output: 0 -> 0.0004 CNY
        # 总开销: 0.018 + 0.0021 + 0.0004 = 0.0205 CNY
        assert abs(summary["estimated_cost_cny"] - 0.0205) < 1e-6
        
        # 2. 验证模型维度 (by_model)
        by_model = data["by_model"]
        assert len(by_model) == 2
        
        # 成本最高排在最前 (deepseek-reasoner 估算成本 0.018, deepseek-chat 估算成本 0.0025)
        assert by_model[0]["model"] == "deepseek-reasoner"
        assert by_model[0]["count"] == 1
        assert by_model[0]["success_rate"] == 1.0
        assert abs(by_model[0]["estimated_cost_cny"] - 0.018) < 1e-6
        
        assert by_model[1]["model"] == "deepseek-chat"
        assert by_model[1]["count"] == 2
        assert by_model[1]["success_rate"] == 0.5
        assert abs(by_model[1]["estimated_cost_cny"] - 0.0025) < 1e-6
        
        # 3. 验证用途维度 (by_purpose)
        by_purpose = data["by_purpose"]
        assert len(by_purpose) == 2
        # brainstorm 有 2 次调用，排在最前
        assert by_purpose[0]["purpose"] == "brainstorm"
        assert by_purpose[0]["count"] == 2
        assert by_purpose[0]["success_rate"] == 0.5
        
        assert by_purpose[1]["purpose"] == "draft"
        assert by_purpose[1]["count"] == 1
        assert by_purpose[1]["success_rate"] == 1.0
        
        # 4. 验证错误统计 (errors)
        errors = data["errors"]
        assert len(errors) == 1
        assert errors[0]["error_code"] == "rate_limit"
        assert errors[0]["count"] == 1
        assert errors[0]["last_message"] == "Rate limit exceeded"
        
        # 5. 验证趋势 (daily_trend)
        daily_trend = data["daily_trend"]
        assert len(daily_trend) == 2
        assert daily_trend[0]["date"] == day1[:10]
        assert daily_trend[0]["count"] == 1
        assert daily_trend[1]["date"] == day2[:10]
        assert daily_trend[1]["count"] == 2
