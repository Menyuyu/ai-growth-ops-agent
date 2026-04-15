"""
策略推荐Agent
连接"目标用户是谁"和"应该说什么"的桥梁
根据用户分层结果和漏斗问题，推荐增长策略
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import LLMClient
from core.data_models import FunnelResult, SegmentResult, StrategyResult


class StrategyAgent:
    """增长策略推荐Agent"""

    # SaaS增长策略知识库
    STRATEGY_KNOWLEDGE = {
        "已注册": {
            "问题": "用户注册后没有下一步动作",
            "策略方向": "降低首次使用门槛，快速展示产品价值",
            "推荐渠道": ["应用内引导", "新手邮件序列", "短信提醒"],
            "信息框架": ["快速入门指南", "模板库展示", "成功案例"],
            "语气": "友好引导型，避免信息过载",
        },
        "已浏览": {
            "问题": "用户浏览了界面但没有创建内容",
            "策略方向": "提供预加载模板，减少冷启动阻力",
            "推荐渠道": ["应用内提示", "邮件案例展示"],
            "信息框架": ["一键模板", "3步出图教程", "同行作品展示"],
            "语气": "鼓励型，强调简单易用",
        },
        "首次使用": {
            "问题": "用户创建了内容但没有持续使用",
            "策略方向": "培养使用习惯，展示进阶功能",
            "推荐渠道": ["应用内推荐", "邮件教育内容", "社群引导"],
            "信息框架": ["进阶技巧", "效率提升案例", "用户故事"],
            "语气": "专业指导型",
        },
        "已活跃": {
            "问题": "活跃用户没有转化为付费",
            "策略方向": "展示Pro功能价值，提供试用激励",
            "推荐渠道": ["应用内升级引导", "限时优惠邮件", "客服主动触达"],
            "信息框架": ["Pro功能对比", "ROI计算", "限时优惠"],
            "语气": "价值导向型，强调投资回报",
        },
        "已付费": {
            "问题": "付费用户没有续费或升级",
            "策略方向": "提升产品粘性，建立长期关系",
            "推荐渠道": ["客户成功邮件", "专属客服", "社区运营"],
            "信息框架": ["新功能预告", "最佳实践", "VIP权益"],
            "语气": "尊享型，强调专属价值",
        },
    }

    # 用户分层策略映射
    SEGMENT_STRATEGIES = {
        "高价值用户": {
            "触达优先级": "最高",
            "策略基调": "VIP专属感",
            "推荐动作": ["专属客户经理", "新品内测邀请", "年度VIP活动"],
        },
        "潜力用户": {
            "触达优先级": "高",
            "策略基调": "引导转化",
            "推荐动作": ["限时优惠", "功能推荐", "使用教程"],
        },
        "发展用户": {
            "触达优先级": "中",
            "策略基调": "持续教育",
            "推荐动作": ["内容营销", "案例分享", "社区参与"],
        },
        "一般用户": {
            "触达优先级": "低",
            "策略基调": "低成本维护",
            "推荐动作": ["自动化邮件", "产品更新通知"],
        },
        "流失预警": {
            "触达优先级": "最高",
            "策略基调": "紧急挽回",
            "推荐动作": ["专属挽回优惠", "满意度调研", "1对1沟通"],
        },
        "流失用户": {
            "触达优先级": "中",
            "策略基调": "低成本召回",
            "推荐动作": ["重大更新通知", "回归优惠", "选择性放弃"],
        },
    }

    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()
        self.history = []

    def recommend(
        self,
        funnel_result: FunnelResult,
        segment_result: SegmentResult,
        aigc_insights: dict = None,
    ) -> StrategyResult:
        """
        基于漏斗诊断和分层结果推荐增长策略

        Args:
            funnel_result: 漏斗诊断结果
            segment_result: 用户分层结果
            aigc_insights: AIGC 行业洞察（可选）

        Returns:
            StrategyResult: 策略推荐结果
        """
        # 1. 从知识库获取基础策略
        problem_stage = funnel_result.problem_stage.split("->")[-1] if "->" in funnel_result.problem_stage else funnel_result.problem_stage
        stage_knowledge = self.STRATEGY_KNOWLEDGE.get(problem_stage, {})
        segment_knowledge = self.SEGMENT_STRATEGIES.get(segment_result.priority_segment, {})

        # 2. 构建 AIGC 上下文（如有）
        aigc_section = ""
        if aigc_insights:
            pain_points = aigc_insights.get("sentiment_analysis", {}).get("top_pain_points", [])[:3]
            key_finding = aigc_insights.get("scene_insights", {}).get("key_finding", {})
            growth_proposal = key_finding.get("growth_proposal", {})

            pain_text = "、".join([pp["chinese"] for pp in pain_points]) if pain_points else "暂无"
            insight_text = key_finding.get("insight", "暂无")
            proposal_name = growth_proposal.get("name", "")
            proposal_desc = growth_proposal.get("description", "")
            proposal_impact = growth_proposal.get("expected_impact", "")

            aigc_section = f"""
【AIGC行业洞察参考】
- 用户核心痛点: {pain_text}
- 场景关键发现: {insight_text}
- 增长方案建议: {proposal_name}
  {proposal_desc}
- 预期影响: {proposal_impact}

请在制定策略时参考上述行业洞察，使策略更有针对性。
"""

        # 3. 用LLM生成定制化策略
        prompt = f"""你是增长运营专家，请基于以下信息推荐增长策略：

【漏斗诊断】
- 问题环节：{funnel_result.problem_stage}
- 流失率：{funnel_result.leak_rate}%
- 实际转化率：{funnel_result.actual_conversion}%
- 行业基准：{funnel_result.benchmark_conversion}%
- 预估影响：{funnel_result.estimated_impact}

【目标用户】
- 优先分层：{segment_result.priority_segment}
- 用户数量：{segment_result.segment_count}人（占比{segment_result.segment_percentage}%）
- 用户画像：{segment_result.segment_profile}

【策略知识库参考】
阶段策略：{stage_knowledge.get("策略方向", "需要进一步分析")}
推荐渠道：{stage_knowledge.get("推荐渠道", [])}
信息框架：{stage_knowledge.get("信息框架", [])}
分层基调：{segment_knowledge.get("策略基调", "通用")}
推荐动作：{segment_knowledge.get("推荐动作", [])}
{aigc_section}
请输出详细策略（JSON格式）：
{{
    "campaign_type": "营销活动类型（如：挽回邮件+应用内提示）",
    "message_framework": "信息框架（如：社交证明+简化路径）",
    "tone_guidance": "语气指导（如：鼓励型、非推销）",
    "cta_recommendation": "CTA文案建议",
    "channel_priority": ["渠道优先级排序"],
    "selected_templates": ["推荐使用的内容模板"],
    "reasoning": "策略推荐理由（100字以内）"
}}"""

        system = "你是一个资深SaaS增长运营专家，擅长基于数据制定增长策略。"
        result_text = self.client.generate(prompt, system_prompt=system, max_tokens=1024)

        # 3. 解析结果
        strategy = self._parse_result(result_text, stage_knowledge, segment_knowledge)

        self.history.append({
            "funnel": funnel_result.problem_stage,
            "segment": segment_result.priority_segment,
            "strategy": strategy,
        })

        return strategy

    def _parse_result(self, result_text, stage_kb, segment_kb):
        """解析LLM返回的策略（兼容JSON和非JSON格式）"""
        import json
        import re

        # 尝试解析JSON
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return StrategyResult(
                    campaign_type=data.get("campaign_type", ""),
                    message_framework=data.get("message_framework", ""),
                    tone_guidance=data.get("tone_guidance", ""),
                    cta_recommendation=data.get("cta_recommendation", ""),
                    channel_priority=data.get("channel_priority", []),
                    selected_templates=data.get("selected_templates", []),
                    reasoning=data.get("reasoning", ""),
                )
        except (json.JSONDecodeError, AttributeError):
            pass

        # 降级：用规则提取
        return StrategyResult(
            campaign_type=stage_kb.get("策略方向", "个性化触达"),
            message_framework=" + ".join(stage_kb.get("信息框架", ["价值展示"])),
            tone_guidance=segment_kb.get("策略基调", "友好引导"),
            cta_recommendation="立即体验",
            channel_priority=stage_kb.get("推荐渠道", ["邮件"]),
            selected_templates=["email_marketing"],
            reasoning=result_text[:200],
        )

    def get_history(self) -> list:
        """获取策略推荐历史"""
        return self.history
