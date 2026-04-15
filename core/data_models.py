"""
统一数据模型
确保所有Agent模块使用相同的数据结构
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class FunnelResult:
    """漏斗诊断结果 → 传递给分层Agent"""
    problem_stage: str  # "注册->首次使用"
    leak_rate: float  # 85.0
    actual_conversion: float  # 15.0
    benchmark_conversion: float  # 30.0
    affected_user_ids: list = field(default_factory=list)
    estimated_impact: str = ""
    benchmark_gap: float = 0.0


@dataclass
class SegmentResult:
    """用户分层结果 → 传递给策略Agent"""
    priority_segment: str  # "流失预警-高价值用户"
    segment_count: int = 0
    segment_percentage: float = 0.0
    segment_profile: str = ""
    target_user_ids: list = field(default_factory=list)
    recommended_intervention: str = ""
    estimated_conversion_uplift: str = ""
    full_segmentation: dict = field(default_factory=dict)


@dataclass
class StrategyResult:
    """策略推荐结果 → 传递给内容Agent"""
    campaign_type: str = ""
    message_framework: str = ""
    tone_guidance: str = ""
    cta_recommendation: str = ""
    channel_priority: list = field(default_factory=list)
    selected_templates: list = field(default_factory=list)
    reasoning: str = ""


@dataclass
class Variant:
    """内容变体"""
    version: str = ""
    content: str = ""
    hypothesis: str = ""


@dataclass
class ContentResult:
    """内容生成结果 → 传递给A/B测试Agent"""
    variants: list = field(default_factory=list)  # List[Variant]
    recommended_ab_setup: str = ""
    personalization_rules: str = ""


@dataclass
class ABResult:
    """A/B测试结果 → 传递给增长记忆"""
    test_name: str = ""
    winning_variant: str = ""
    statistical_significance: float = 0.0
    p_value: float = 0.0
    actual_uplift: str = ""
    downstream_impact: str = ""
    estimated_monthly_impact: str = ""
    recommendation: str = ""
    full_report: str = ""
    conversion_a: float = 0.0
    conversion_b: float = 0.0


@dataclass
class GrowthMemory:
    """增长知识库"""
    segment_strategies: dict = field(default_factory=dict)  # segment -> best_strategy
    funnel_improvements: list = field(default_factory=list)
    content_template_rankings: dict = field(default_factory=dict)


@dataclass
class GrowthCycle:
    """一次完整的增长周期"""
    cycle_id: int = 0
    scenario_name: str = ""
    timestamp: str = ""
    funnel_result: Optional[FunnelResult] = None
    segment_result: Optional[SegmentResult] = None
    strategy_result: Optional[StrategyResult] = None
    content_result: Optional[ContentResult] = None
    ab_result: Optional[ABResult] = None
    growth_memory: Optional[GrowthMemory] = None
    aigc_insights: Optional[dict] = None
    status: str = "running"  # running | completed
