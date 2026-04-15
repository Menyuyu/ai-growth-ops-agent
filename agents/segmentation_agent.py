"""
用户智能分层Agent
基于 RFM 模型 + 漏斗阶段 + 流失风险评分，定位高优先级目标群体
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from core.llm_client import LLMClient
from core.data_models import FunnelResult, SegmentResult


# RFM 分层到优先级分层的映射
RFM_TO_PRIORITY = {
    "高价值用户": "高优先级",
    "潜力用户": "高优先级",
    "流失预警": "高优先级",
    "发展用户": "中优先级",
    "一般用户": "低优先级",
    "流失用户": "低优先级",
    "其他用户": "观察区",
}

PRIORITY_TO_INTERVENTION = {
    "高优先级": "立即触达：个性化挽回邮件 + 应用内提示 + 专属优惠",
    "中优先级": "计划触达：教育内容 + 功能推荐 + 限时激励",
    "低优先级": "自动化触达：产品更新通知 + 内容营销",
    "观察区": "持续观察，收集更多行为数据",
}

PRIORITY_TO_UPLIFT = {
    "高优先级": "15-25%转化提升",
    "中优先级": "8-15%转化提升",
    "低优先级": "3-8%转化提升",
}


class SegmentationAgent:
    """用户智能分层Agent"""

    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()
        self.segmented_data = None

    def analyze(
        self,
        df: pd.DataFrame,
        funnel_result: FunnelResult = None,
        use_rfm: bool = True,
    ) -> SegmentResult:
        """
        对用户数据进行智能分层分析

        Args:
            df: 用户数据DataFrame
            funnel_result: 漏斗诊断结果（可选，用于聚焦受影响用户）
            use_rfm: 是否使用 RFM 模型分层（默认True）

        Returns:
            SegmentResult: 分层结果
        """
        # 如果有漏斗结果，聚焦受影响用户
        if funnel_result and funnel_result.affected_user_ids:
            df = df[df["user_id"].isin(funnel_result.affected_user_ids)].copy()

        # 综合评分分层
        if use_rfm:
            df_scored = self._rfm_segmentation(df)
        else:
            df_scored = self._calculate_priority_scores(df)
        self.segmented_data = df_scored

        # 找到优先级最高的分层
        priority = self._identify_priority_segment(df_scored, funnel_result)

        return SegmentResult(
            priority_segment=priority["name"],
            segment_count=priority["count"],
            segment_percentage=priority["percentage"],
            segment_profile=priority["profile"],
            target_user_ids=priority["user_ids"],
            recommended_intervention=priority["intervention"],
            estimated_conversion_uplift=priority["estimated_uplift"],
            full_segmentation=self._get_segment_summary(df_scored),
        )

    def _rfm_segmentation(self, df: pd.DataFrame) -> pd.DataFrame:
        """使用 RFM 模型进行用户分层"""
        from utils.rfm import calculate_rfm_scores, segment_users, SEGMENT_STRATEGIES

        df = df.copy()

        # 检查是否有 RFM 所需字段
        has_rfm = all(c in df.columns for c in ["recency_days", "frequency_sessions", "monetary_spent"])
        if not has_rfm:
            return self._calculate_priority_scores(df)

        # 计算 RFM 分数
        df = calculate_rfm_scores(df, recency_col="recency_days", frequency_col="frequency_sessions", monetary_col="monetary_spent")

        # 基于 RFM 分层
        df = segment_users(df)

        # 映射到优先级分层
        df["priority_segment"] = df["segment"].map(RFM_TO_PRIORITY).fillna("观察区")
        df["segment_strategy"] = df["segment"].map(SEGMENT_STRATEGIES).fillna("需要进一步分析")

        # 结合漏斗阶段细化
        if "funnel_stage" in df.columns:
            stage_map = {"已付费": "已付费用户", "已活跃": "活跃用户",
                        "首次使用": "新手用户", "已浏览": "浏览用户", "已注册": "注册未激活"}
            df["detailed_segment"] = df["priority_segment"] + "-" + df["funnel_stage"].map(stage_map).fillna(df["funnel_stage"])
        else:
            df["detailed_segment"] = df["priority_segment"]

        return df

    def _calculate_priority_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算综合优先级评分"""
        df = df.copy()

        # 基于已有字段计算综合分数
        df["priority_score"] = 0

        # 流失风险（分数越高风险越大）
        if "churn_risk_score" in df.columns:
            df["priority_score"] += df["churn_risk_score"]

        # 价值贡献
        if "monetary_spent" in df.columns:
            max_m = df["monetary_spent"].max() or 1
            df["priority_score"] += (df["monetary_spent"] / max_m) * 30

        # 使用深度
        if "design_count" in df.columns:
            max_d = df["design_count"].max() or 1
            df["priority_score"] += (df["design_count"] / max_d) * 20

        # 归一化到0-100
        max_score = df["priority_score"].max() or 1
        df["priority_score"] = (df["priority_score"] / max_score * 100).round(1)

        # 综合分层
        conditions = [
            df["priority_score"] >= 70,
            (df["priority_score"] >= 50) & (df["priority_score"] < 70),
            (df["priority_score"] >= 30) & (df["priority_score"] < 50),
            df["priority_score"] < 30,
        ]
        labels = ["高优先级", "中优先级", "低优先级", "观察区"]
        df["priority_segment"] = np.select(conditions, labels, default="观察区")

        # 结合漏斗阶段细化
        if "funnel_stage" in df.columns:
            stage_map = {"已付费": "已付费用户", "已活跃": "活跃用户",
                        "首次使用": "新手用户", "已浏览": "浏览用户", "已注册": "注册未激活"}
            df["detailed_segment"] = df["priority_segment"] + "-" + df["funnel_stage"].map(stage_map).fillna(df["funnel_stage"])
        else:
            df["detailed_segment"] = df["priority_segment"]

        return df

    def _identify_priority_segment(self, df, funnel_result):
        """识别最优先处理的分层"""
        # 按优先级排序
        segment_groups = df.groupby("priority_segment")

        # 优先选择"高优先级"群体
        for priority in ["高优先级", "中优先级", "低优先级"]:
            if priority in segment_groups.groups:
                group = segment_groups.get_group(priority)
                if len(group) > 0:
                    profile = self._generate_profile(group)
                    intervention = self._recommend_intervention(priority, funnel_result)
                    return {
                        "name": priority,
                        "count": len(group),
                        "percentage": round(len(group) / len(df) * 100, 1),
                        "profile": profile,
                        "user_ids": group["user_id"].tolist()[:50],
                        "intervention": intervention,
                        "estimated_uplift": self._estimate_uplift(priority),
                    }

        return {
            "name": "观察区",
            "count": len(df),
            "percentage": 100.0,
            "profile": "需要进一步数据积累",
            "user_ids": [],
            "intervention": "持续观察，收集更多行为数据",
            "estimated_uplift": "暂无法估算",
        }

    def _generate_profile(self, group: pd.DataFrame) -> str:
        """生成用户画像描述"""
        avg_risk = group.get("churn_risk_score", pd.Series([50])).mean()
        avg_designs = group.get("design_count", pd.Series([0])).mean()
        avg_sessions = group.get("frequency_sessions", pd.Series([0])).mean()

        risk_label = "高" if avg_risk > 60 else "中" if avg_risk > 30 else "低"
        engagement = "活跃" if avg_designs > 5 else "中等" if avg_designs > 1 else "低"

        return f"流失风险{risk_label}，使用活跃度{engagement}（平均{avg_designs:.1f}个设计，{avg_sessions:.1f}次会话）"

    def _recommend_intervention(self, priority, funnel_result):
        """推荐干预措施"""
        return PRIORITY_TO_INTERVENTION.get(priority, "持续观察")

    def _estimate_uplift(self, priority):
        """预估转化提升"""
        return PRIORITY_TO_UPLIFT.get(priority, "待验证")

    def _get_segment_summary(self, df):
        """获取分层概览"""
        summary = df["priority_segment"].value_counts().to_dict()
        return {k: {"count": int(v), "pct": round(v / len(df) * 100, 1)} for k, v in summary.items()}

    def generate_llm_strategies(self, segment_result: SegmentResult) -> str:
        """用LLM为优先分层生成详细策略"""
        prompt = (
            f"你是增长运营专家，请为以下用户群体制定详细的运营策略：\n\n"
            f"用户分层：{segment_result.priority_segment}\n"
            f"用户数量：{segment_result.segment_count}人（占比{segment_result.segment_percentage}%）\n"
            f"用户画像：{segment_result.segment_profile}\n"
            f"推荐干预：{segment_result.recommended_intervention}\n\n"
            f"请详细输出以下内容（总字数不少于300字）：\n"
            f"1. **用户画像详细描述**：从行为特征、心理特征、使用习惯三个维度深入分析（100字以上）\n"
            f"2. **核心运营目标**：明确短期和长期目标，量化预期效果\n"
            f"3. **具体运营策略**：至少5条可执行动作，每条包含具体步骤和预期效果\n"
            f"4. **推荐触达渠道和时机**：按优先级排序，说明每个渠道的最佳触达时机\n"
            f"5. **预期效果指标**：列出3-5个核心指标和预期提升幅度"
        )

        system = "你是一个SaaS增长运营专家，擅长用户分层运营策略制定。"
        return self.client.generate(prompt, system_prompt=system, max_tokens=1024)
