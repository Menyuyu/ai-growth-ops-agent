"""
API 请求/响应模型
"""

from pydantic import BaseModel
from typing import Optional, Any


# ========== 漏斗诊断 ==========

class DiagnoseRequest(BaseModel):
    """漏斗诊断请求"""
    scenario_name: str = "SaaS增长周期"


class DiagnoseResponse(BaseModel):
    """漏斗诊断响应"""
    problem_stage: str
    leak_rate: float
    actual_conversion: float
    benchmark_conversion: float
    estimated_impact: str
    benchmark_gap: float


# ========== 用户分层 ==========

class SegmentRequest(BaseModel):
    """用户分层请求"""
    scenario_name: str = "SaaS增长周期"


class SegmentResponse(BaseModel):
    """用户分层响应"""
    priority_segment: str
    segment_count: int
    segment_percentage: float
    segment_profile: str
    recommended_intervention: str
    estimated_conversion_uplift: str


# ========== 策略推荐 ==========

class StrategyRequest(BaseModel):
    """策略推荐请求"""
    scenario_name: str = "SaaS增长周期"


class StrategyResponse(BaseModel):
    """策略推荐响应"""
    campaign_type: str
    message_framework: str
    tone_guidance: str
    cta_recommendation: str
    channel_priority: list
    selected_templates: list
    reasoning: str


# ========== 内容生成 ==========

class ContentRequest(BaseModel):
    """内容生成请求"""
    scenario_name: str = "SaaS增长周期"
    variant_count: int = 3


class ContentVariant(BaseModel):
    """内容变体"""
    version: str
    content: str
    hypothesis: str


class ContentResponse(BaseModel):
    """内容生成响应"""
    variants: list[ContentVariant]
    recommended_ab_setup: str


# ========== A/B测试 ==========

class ABTestRequest(BaseModel):
    """A/B测试请求"""
    conversions_a: int
    n_a: int
    conversions_b: int
    n_b: int
    test_name: str = "A/B测试"


class ABTestResponse(BaseModel):
    """A/B测试响应"""
    winning_variant: str
    p_value: float
    actual_uplift: str
    estimated_monthly_impact: str
    recommendation: str
    full_report: str


# ========== 增长记忆 ==========

class MemoryRecordRequest(BaseModel):
    """记录实验结果请求"""
    segment: str
    strategy: str
    significant: bool
    winning_variant: str
    lift_percent: float


class MemoryResponse(BaseModel):
    """知识库响应"""
    knowledge_report: str
