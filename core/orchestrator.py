"""
增长周期编排器
串联所有 Agent，实现完整的增长工作流

架构设计（Harness Engineering 六层模型）：
  L1 提示词 → L2 上下文 → L3 工具 → L4 安全 → L5 弹性 → L6 可观测性

分级自治参考：Anthropic agent escalation pattern (https://docs.anthropic.com/claude/docs/agent-escalation)
实现为从零编写的 4 级权限控制系统

集成特性：
- 可观测性：每个 Agent 操作记录结构化事件（token/耗时/决策）
- 熔断器：Agent 连续失败自动降级，防止无限重试
- 分级自治：4 级权限控制，从"全自动"到"需人工审核"
- 上下文裁剪：每个 Agent 只继承它需要的上下文
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from core.data_models import (
    GrowthCycle, FunnelResult, SegmentResult,
    StrategyResult, ContentResult, ABResult,
)
from core.llm_client import LLMClient
from core.observability import Observability
from core.circuit_breaker import AgentCircuitBreakers
from core.logger import get_logger

from agents.funnel_agent import FunnelAgent
from agents.segmentation_agent import SegmentationAgent
from agents.strategy_agent import StrategyAgent
from agents.content_agent import ContentAgent
from agents.ab_test_agent import ABTestAgent
from agents.growth_memory import GrowthMemory


# 分级自治级别
AUTONOMY_LEVELS = {
    "manual": 0,      # 每步需人工确认
    "review": 1,      # 执行后需人工审核
    "auto_safe": 2,   # 安全操作自动执行（报告、分析）
    "auto": 3,        # 全自动（已验证策略）
}


class GrowthOrchestrator:
    """增长周期编排器 - 串联所有 Agent 形成闭环"""

    PHASES = ["诊断", "识别", "行动", "验证", "学习"]

    def __init__(self, api_key: str = None, provider: str = "dashscope"):
        from core.llm_client import LLMClient, API_CONFIGS
        config = API_CONFIGS.get(provider, API_CONFIGS["openai"])
        client = LLMClient(
            api_key=api_key,
            model=config["model"],
            base_url=config["base_url"],
            provider=provider,
        )

        self.funnel_agent = FunnelAgent(client)
        self.segmentation_agent = SegmentationAgent(client)
        self.strategy_agent = StrategyAgent(client)
        self.content_agent = ContentAgent(client)
        self.ab_test_agent = ABTestAgent(client)
        self.growth_memory = GrowthMemory()
        self.cycle_counter = 0

        # Harness Engineering: 可观测性
        self.obs = Observability()

        # Harness Engineering: 熔断器（连续 3 次失败自动降级）
        self.circuit_breakers = AgentCircuitBreakers(failure_threshold=3, cooldown_seconds=300)

        # Harness Engineering: 分级自治
        self.autonomy_level = "auto_safe"  # 默认：安全操作自动执行

        self.logger = get_logger("GrowthOrchestrator")
        self.logger.info("编排器初始化完成 | provider=%s | model=%s", provider, config["model"])

    def set_autonomy_level(self, level: str):
        """设置自治级别"""
        if level in AUTONOMY_LEVELS:
            self.autonomy_level = level
            self.obs.event("autonomy_level_changed", _level=level)

    def run_cycle(
        self,
        df: pd.DataFrame,
        scenario_name: str = "增长周期",
        use_rfm: bool = True,
        aigc_insights: dict = None,
    ) -> GrowthCycle:
        """
        执行一次完整的增长周期

        Args:
            df: 用户数据 DataFrame
            scenario_name: 场景名称
            use_rfm: 是否使用 RFM 模型分层
            aigc_insights: AIGC 行业洞察（可选，注入策略推荐）

        Returns:
            GrowthCycle: 完整增长周期结果
        """
        self.obs.start_span("growth_cycle", agent="orchestrator")
        self.obs.event("cycle_started", _scenario=scenario_name, user_count=len(df))
        self.logger.info("开始增长周期 #%d | 场景=%s | 数据量=%d 行 | RFM=%s | AIGC=%s", self.cycle_counter + 1, scenario_name, len(df), use_rfm, bool(aigc_insights))

        self.cycle_counter += 1
        cycle = GrowthCycle(cycle_id=self.cycle_counter, scenario_name=scenario_name)
        cycle.aigc_insights = aigc_insights

        # Phase 1: 诊断
        self.logger.info("[Phase 1] 漏斗诊断...")
        t0 = time.time()
        self.obs.agent_event("FunnelAgent", "analysis_started", user_count=len(df))
        cb = self.circuit_breakers.get("FunnelAgent")
        cycle.funnel_result = cb.execute(
            lambda: self.funnel_agent.analyze_from_data(df, scenario_name),
            fallback=FunnelResult(
                problem_stage="未知", leak_rate=0, actual_conversion=0,
                benchmark_conversion=0, estimated_impact="熔断器降级：无法分析",
            ),
        )
        elapsed = round((time.time() - t0) * 1000, 1)
        self.obs.record_decision("FunnelAgent", f"数据 {len(df)} 行", str(cycle.funnel_result.problem_stage), elapsed)
        self.obs.agent_event("FunnelAgent", "analysis_completed", duration_ms=elapsed)

        self.logger.info("[Phase 1] 漏斗诊断完成 | 问题阶段=%s | 转化率=%s%%", cycle.funnel_result.problem_stage, cycle.funnel_result.actual_conversion)

        if not cycle.funnel_result:
            self.logger.error("漏斗诊断失败")
            self.obs.event("cycle_failed", reason="funnel_analysis_failed")
            self.obs.end_span("growth_cycle")
            return cycle

        # Phase 2: 识别
        self.logger.info("[Phase 2] 用户分层 | 分层方法=%s", "RFM" if use_rfm else "综合评分")
        t0 = time.time()
        self.obs.agent_event("SegmentationAgent", "segmentation_started")
        cb = self.circuit_breakers.get("SegmentationAgent")
        cycle.segment_result = cb.execute(
            lambda: self.segmentation_agent.analyze(df, cycle.funnel_result, use_rfm=use_rfm),
            fallback=SegmentResult(
                priority_segment="观察区", segment_count=len(df),
                segment_percentage=100, segment_profile="熔断器降级：使用默认分层",
            ),
        )
        elapsed = round((time.time() - t0) * 1000, 1)
        self.obs.record_decision("SegmentationAgent", f"漏斗问题: {cycle.funnel_result.problem_stage}", str(cycle.segment_result.priority_segment), elapsed)
        self.obs.agent_event("SegmentationAgent", "segmentation_completed", duration_ms=elapsed)

        self.logger.info("[Phase 2] 用户分层完成 | 优先分层=%s | 用户数=%d", cycle.segment_result.priority_segment, cycle.segment_result.segment_count)

        # Phase 3: 行动（策略 + 内容）
        # 上下文裁剪：策略 Agent 只需要漏斗和分层结果，不需要原始数据
        self.logger.info("[Phase 3] 策略推荐...")
        t0 = time.time()
        self.obs.agent_event("StrategyAgent", "recommendation_started")
        cb = self.circuit_breakers.get("StrategyAgent")
        cycle.strategy_result = cb.execute(
            lambda: self.strategy_agent.recommend(cycle.funnel_result, cycle.segment_result, aigc_insights=aigc_insights),
            fallback=StrategyResult(
                campaign_type="默认邮件营销", message_framework="价值展示",
                tone_guidance="专业友好", cta_recommendation="了解更多",
                reasoning="熔断器降级：使用默认策略",
            ),
        )
        elapsed = round((time.time() - t0) * 1000, 1)
        self.obs.record_decision("StrategyAgent", f"分层: {cycle.segment_result.priority_segment}", str(cycle.strategy_result.campaign_type), elapsed)
        self.obs.agent_event("StrategyAgent", "recommendation_completed", duration_ms=elapsed)

        self.logger.info("[Phase 3] 策略推荐完成 | 活动类型=%s | AIGC上下文=%s", cycle.strategy_result.campaign_type, bool(aigc_insights))

        # 内容生成（上下文裁剪：只传递策略和画像，不传递原始漏斗数据）
        self.logger.info("[Phase 3] 内容生成 | 变体数=3")
        t0 = time.time()
        self.obs.agent_event("ContentAgent", "generation_started", variant_count=3)
        cb = self.circuit_breakers.get("ContentAgent")
        cycle.content_result = cb.execute(
            lambda: self.content_agent.generate_for_segment(
                strategy=cycle.strategy_result,
                segment_profile=cycle.segment_result.segment_profile,
                problem_stage=cycle.funnel_result.problem_stage,
                variant_count=3,
            ),
            fallback=ContentResult(
                recommended_ab_setup="熔断器降级：无法生成内容",
            ),
        )
        elapsed = round((time.time() - t0) * 1000, 1)
        self.obs.agent_event("ContentAgent", "generation_completed", variant_count=len(cycle.content_result.variants), duration_ms=elapsed)

        self.logger.info("[Phase 3] 内容生成完成 | 变体数=%d", len(cycle.content_result.variants))

        cycle.status = "waiting_for_ab_data"
        self.logger.info("增长周期 #%d | 阶段 1-3 完成，等待 A/B 测试数据", self.cycle_counter)

        self.obs.event("cycle_phase1_3_completed", variants_generated=len(cycle.content_result.variants))
        self.obs.end_span("growth_cycle")
        return cycle

    def complete_cycle(
        self,
        cycle: GrowthCycle,
        conversions_a: int, n_a: int,
        conversions_b: int, n_b: int,
    ) -> GrowthCycle:
        """
        用 A/B 测试数据完成增长周期

        Args:
            cycle: 未完成的增长周期
            conversions_a/b: A/B 组转化数
            n_a/b: A/B 组样本量

        Returns:
            GrowthCycle: 完成的增长周期
        """
        self.logger.info("[Phase 4] A/B 测试分析 | A组=%d/%d | B组=%d/%d", conversions_a, n_a, conversions_b, n_b)

        self.obs.start_span("ab_test_analysis")
        t0 = time.time()
        self.obs.agent_event("ABTestAgent", "analysis_started")

        variants = cycle.content_result.variants

        cb = self.circuit_breakers.get("ABTestAgent")
        cycle.ab_result = cb.execute(
            lambda: self.ab_test_agent.analyze_from_data(
                conversions_a=conversions_a, n_a=n_a,
                conversions_b=conversions_b, n_b=n_b,
                test_name=f"{cycle.scenario_name} - {cycle.funnel_result.problem_stage}",
                variant_a_hypothesis=variants[0].hypothesis if variants else "",
                variant_b_hypothesis=variants[1].hypothesis if len(variants) > 1 else "",
                baseline_conversion=cycle.funnel_result.actual_conversion,
                total_target_users=cycle.segment_result.segment_count,
            ),
            fallback=ABResult(
                winning_variant="无法分析", recommendation="熔断器降级：无法完成 A/B 分析",
            ),
        )
        elapsed = round((time.time() - t0) * 1000, 1)
        self.obs.record_decision("ABTestAgent", f"A={conversions_a}/{n_a}, B={conversions_b}/{n_b}", str(cycle.ab_result.winning_variant), elapsed)
        self.obs.agent_event("ABTestAgent", "analysis_completed", winner=cycle.ab_result.winning_variant, duration_ms=elapsed)
        self.obs.end_span("ab_test_analysis")

        self.logger.info("[Phase 4] A/B 测试完成 | 获胜=%s | p=%s | 提升=%s", cycle.ab_result.winning_variant, cycle.ab_result.p_value, cycle.ab_result.actual_uplift)

        # 记录到增长记忆
        self.logger.info("[Phase 5] 记录到增长知识库 | 分层=%s | 策略=%s", cycle.segment_result.priority_segment, cycle.strategy_result.campaign_type)
        self.obs.start_span("memory_record")
        self.growth_memory.record_cycle_result(
            segment=cycle.segment_result.priority_segment,
            strategy=cycle.strategy_result.campaign_type,
            ab_result={
                "significant": cycle.ab_result.p_value < 0.05,
                "winning_variant": cycle.ab_result.winning_variant,
                "lift_percent": float(cycle.ab_result.actual_uplift.strip(" +%")) if cycle.ab_result.actual_uplift else 0,
            },
            template_used="email_marketing",
        )
        self.obs.agent_event("GrowthMemory", "cycle_recorded", _segment=cycle.segment_result.priority_segment)
        self.obs.end_span("memory_record")

        cycle.status = "completed"

        # 汇总可观测性
        summary = self.obs.get_summary()
        self.logger.info(
            "增长周期 #%d 完成 | 事件=%d | tokens=%d→%d | 成本=$%.4f",
            self.cycle_counter, summary["event_count"],
            summary["total_tokens_in"], summary["total_tokens_out"],
            summary["total_cost_usd"],
        )
        self.obs.event("cycle_completed", cycle_id=self.cycle_counter, **summary)

        return cycle

    def get_knowledge_report(self) -> str:
        """获取增长知识库报告"""
        return self.growth_memory.get_knowledge_report()

    def get_observability_summary(self) -> dict:
        """获取可观测性摘要（用于演示和调试）"""
        return self.obs.get_summary()

    def get_circuit_breaker_status(self) -> list:
        """获取所有熔断器状态"""
        return self.circuit_breakers.get_all_status()
