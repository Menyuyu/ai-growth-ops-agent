"""
转化漏斗诊断Agent
自动定位流失环节，识别受影响用户，生成优化建议
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from core.llm_client import LLMClient
from core.data_models import FunnelResult


class FunnelAgent:
    """转化漏斗诊断Agent"""

    # SaaS漏斗基准转化率
    SAAS_BENCHMARKS = {
        "已注册->已浏览": 85,
        "已浏览->首次使用": 55,
        "首次使用->已活跃": 50,
        "已活跃->已付费": 25,
    }

    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()

    def analyze_from_data(
        self,
        df: pd.DataFrame,
        funnel_name: str = "SaaS用户转化漏斗",
    ) -> FunnelResult:
        """
        从用户数据自动计算漏斗并诊断

        Args:
            df: 用户数据DataFrame（需包含funnel_stage列）
            funnel_name: 漏斗名称

        Returns:
            FunnelResult: 诊断结果
        """
        funnel_order = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]

        # 计算各阶段用户数（累计：到达某阶段及以上的用户）
        stage_counts = df["funnel_stage"].value_counts()
        raw_counts = {s: int(stage_counts.get(s, 0)) for s in funnel_order}
        # 累计计数：已注册 = 所有人，已浏览 = 到达已浏览及以上，...
        cumulative_counts = {}
        running_total = 0
        for s in reversed(funnel_order):
            running_total += raw_counts.get(s, 0)
            cumulative_counts[s] = running_total

        stage_users = [{"name": s, "users": cumulative_counts[s]} for s in funnel_order]

        # 计算转化率
        stage_data = []
        for i, stage in enumerate(stage_users):
            if i == 0:
                conversion_rate = 100.0
                dropoff = 0
            else:
                prev = stage_users[i - 1]["users"]
                conversion_rate = (stage["users"] / prev * 100) if prev > 0 else 0
                dropoff = prev - stage["users"]

            stage_data.append({
                "name": stage["name"],
                "users": stage["users"],
                "conversion_rate": round(conversion_rate, 1),
                "dropoff": dropoff,
            })

        # 找到最严重的问题环节
        worst_stage = self._find_worst_stage(stage_data)

        # 识别受影响的用户
        affected_ids = self._identify_affected_users(df, worst_stage, funnel_order)

        # 估算影响
        total_users = stage_users[0]["users"]
        benchmark = self.SAAS_BENCHMARKS.get(worst_stage, 50)
        actual = next((s["conversion_rate"] for s in stage_data if s["name"] == worst_stage.split("->")[-1]), 0)
        gap = benchmark - actual
        recovered = int(total_users * gap / 100 * 0.3)  # 假设能挽回30%的差距
        impact = f"若提升到行业基准，预计每月可多激活约{recovered}名用户"

        return FunnelResult(
            problem_stage=worst_stage,
            leak_rate=round(100 - actual, 1),
            actual_conversion=round(actual, 1),
            benchmark_conversion=benchmark,
            affected_user_ids=affected_ids,
            estimated_impact=impact,
            benchmark_gap=round(gap, 1),
        )

    def analyze_from_stages(
        self,
        funnel_stages: list,
        funnel_name: str = "用户转化漏斗",
    ) -> FunnelResult:
        """从手动输入的漏斗阶段分析（兼容旧接口）"""
        stage_data = []
        for i, stage in enumerate(funnel_stages):
            if i == 0:
                conversion_rate = 100.0
                dropoff = 0
            else:
                prev = funnel_stages[i - 1]["users"]
                conversion_rate = (stage["users"] / prev * 100) if prev > 0 else 0
                dropoff = prev - stage["users"]
            stage_data.append({
                "name": stage["name"],
                "users": stage["users"],
                "conversion_rate": round(conversion_rate, 1),
                "dropoff": dropoff,
            })

        worst_stage = self._find_worst_stage(stage_data)
        actual = next((s["conversion_rate"] for s in stage_data if s["name"] == worst_stage.split("->")[-1]), 0)
        benchmark = self.SAAS_BENCHMARKS.get(worst_stage, 50)

        total_users = funnel_stages[0]["users"]
        gap = benchmark - actual
        recovered = int(total_users * gap / 100 * 0.3)

        return FunnelResult(
            problem_stage=worst_stage,
            leak_rate=round(100 - actual, 1),
            actual_conversion=round(actual, 1),
            benchmark_conversion=benchmark,
            affected_user_ids=[],
            estimated_impact=f"若提升到行业基准，预计每月可多激活约{recovered}名用户",
            benchmark_gap=round(gap, 1),
        )

    def generate_report(self, funnel_result: FunnelResult) -> str:
        """基于诊断结果生成LLM报告"""
        prompt = (
            f"你是SaaS增长运营专家，请对以下漏斗问题进行诊断分析：\n\n"
            f"问题环节：{funnel_result.problem_stage}\n"
            f"流失率：{funnel_result.leak_rate}%\n"
            f"实际转化率：{funnel_result.actual_conversion}%\n"
            f"行业基准：{funnel_result.benchmark_conversion}%\n"
            f"差距：{funnel_result.benchmark_gap}个百分点\n"
            f"预估影响：{funnel_result.estimated_impact}\n\n"
            f"请针对「{funnel_result.problem_stage}」环节的问题，输出：\n"
            f"1. 问题根因分析（2-3条，必须提及「{funnel_result.problem_stage}」这个环节的具体问题）\n"
            f"2. 具体优化建议（3-5条可执行方案，针对「{funnel_result.problem_stage}」环节）\n"
            f"3. 优先级排序\n"
            f"4. 预期效果评估"
        )

        system = "你是一个SaaS增长运营专家，擅长漏斗分析和优化。"
        return self.client.generate(prompt, system_prompt=system, max_tokens=1024)

    def _find_worst_stage(self, stage_data: list) -> str:
        """找到转化率最低的环节"""
        worst = None
        worst_rate = 100
        for i in range(1, len(stage_data)):
            rate = stage_data[i]["conversion_rate"]
            if rate < worst_rate:
                worst_rate = rate
                worst = f"{stage_data[i-1]['name']}->{stage_data[i]['name']}"
        return worst or "未知"

    def _identify_affected_users(self, df, worst_stage, funnel_order) -> list:
        """识别在问题环节流失的用户"""
        stage_name = worst_stage.split("->")[-1]
        idx = funnel_order.index(stage_name) if stage_name in funnel_order else -1
        if idx <= 0:
            return df["user_id"].tolist()

        # 找到在目标阶段之前的用户
        prev_stage = funnel_order[idx - 1]
        affected = df[df["funnel_stage"] == prev_stage]["user_id"].tolist()
        return affected[:100]  # 限制数量
