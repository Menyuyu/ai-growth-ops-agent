"""
FastAPI 服务
将增长运营系统的6个Agent暴露为REST API
供 n8n 工作流调用
每个端点只执行对应的Agent步骤，独立快速
"""

import sys
import os

# 绝对路径加载 .env
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
from dotenv import load_dotenv
load_dotenv(ENV_FILE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 验证 API Key 已加载
_api_key = os.getenv("DASHSCOPE_API_KEY", "")
if not _api_key:
    print(f"WARNING: No API key found. Checked: {ENV_FILE}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from core.llm_client import LLMClient
from agents.funnel_agent import FunnelAgent
from agents.segmentation_agent import SegmentationAgent
from agents.strategy_agent import StrategyAgent
from agents.content_agent import ContentAgent
from agents.ab_test_agent import ABTestAgent
from agents.growth_memory import GrowthMemory
from core.data_models import FunnelResult, SegmentResult, StrategyResult

# ========== 初始化 ==========
app = FastAPI(title="GrowthLoop AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载数据
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "mock_users_saas.csv")
user_df = pd.read_csv(DATA_FILE)

# 初始化客户端和Agent
api_key = os.getenv("OPENAI_API_KEY", os.getenv("DASHSCOPE_API_KEY", ""))
provider = os.getenv("API_PROVIDER", "dashscope")
llm_client = LLMClient(api_key=api_key, provider=provider)

funnel_agent = FunnelAgent(llm_client)
segmentation_agent = SegmentationAgent(llm_client)
strategy_agent = StrategyAgent(llm_client)
content_agent = ContentAgent(llm_client)
ab_test_agent = ABTestAgent(llm_client)
growth_memory = GrowthMemory()


# ========== API端点 ==========

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "users_loaded": len(user_df)}


@app.post("/api/diagnose")
def diagnose():
    """
    阶段1: 漏斗诊断
    自动分析用户漏斗，找到最严重的流失环节
    """
    try:
        result = funnel_agent.analyze_from_data(user_df, "SaaS增长周期")
        return {
            "problem_stage": result.problem_stage,
            "leak_rate": result.leak_rate,
            "actual_conversion": result.actual_conversion,
            "benchmark_conversion": result.benchmark_conversion,
            "estimated_impact": result.estimated_impact,
            "benchmark_gap": result.benchmark_gap,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/segment")
def segment():
    """
    阶段2: 用户分层
    基于诊断结果定位高优先级目标用户群体
    """
    try:
        # 先诊断获取漏斗结果
        funnel_result = funnel_agent.analyze_from_data(user_df, "SaaS增长周期")
        result = segmentation_agent.analyze(user_df, funnel_result)
        return {
            "priority_segment": result.priority_segment,
            "segment_count": result.segment_count,
            "segment_percentage": result.segment_percentage,
            "segment_profile": result.segment_profile,
            "recommended_intervention": result.recommended_intervention,
            "estimated_conversion_uplift": result.estimated_conversion_uplift,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategy")
def strategy():
    """
    阶段3a: 策略推荐
    根据漏斗问题和用户分层推荐增长策略
    """
    try:
        funnel_result = funnel_agent.analyze_from_data(user_df, "SaaS增长周期")
        segment_result = segmentation_agent.analyze(user_df, funnel_result)
        result = strategy_agent.recommend(funnel_result, segment_result)
        return {
            "campaign_type": result.campaign_type,
            "message_framework": result.message_framework,
            "tone_guidance": result.tone_guidance,
            "cta_recommendation": result.cta_recommendation,
            "channel_priority": result.channel_priority,
            "selected_templates": result.selected_templates,
            "reasoning": result.reasoning,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
def generate(variant_count: int = 3):
    """
    阶段3b: 内容生成
    基于策略生成多个内容变体，各带可验证假设
    """
    try:
        funnel_result = funnel_agent.analyze_from_data(user_df, "SaaS增长周期")
        segment_result = segmentation_agent.analyze(user_df, funnel_result)
        strat_result = strategy_agent.recommend(funnel_result, segment_result)
        result = content_agent.generate_for_segment(
            strategy=strat_result,
            segment_profile=segment_result.segment_profile,
            problem_stage=funnel_result.problem_stage,
            variant_count=variant_count,
        )
        return {
            "variants": [
                {"version": v.version, "content": v.content, "hypothesis": v.hypothesis}
                for v in result.variants
            ],
            "recommended_ab_setup": result.recommended_ab_setup,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/abtest")
def abtest(
    conversions_a: int, n_a: int,
    conversions_b: int, n_b: int,
    test_name: str = "A/B测试",
):
    """
    阶段4: A/B测试分析
    输入实验数据，返回获胜版本和商业影响
    """
    try:
        funnel_result = funnel_agent.analyze_from_data(user_df, "SaaS增长周期")
        result = ab_test_agent.analyze_from_data(
            conversions_a=conversions_a, n_a=n_a,
            conversions_b=conversions_b, n_b=n_b,
            test_name=test_name,
            baseline_conversion=funnel_result.actual_conversion,
            total_target_users=50,  # 模拟目标用户数
        )
        return {
            "winning_variant": result.winning_variant,
            "p_value": result.p_value,
            "actual_uplift": result.actual_uplift,
            "estimated_monthly_impact": result.estimated_monthly_impact,
            "recommendation": result.recommendation,
            "full_report": result.full_report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory")
def get_memory():
    """
    阶段5: 获取增长知识库
    """
    try:
        report = growth_memory.get_knowledge_report()
        return {"knowledge_report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/record")
def record_memory(
    segment: str,
    strategy: str,
    significant: bool,
    winning_variant: str = "",
    lift_percent: float = 0,
):
    """
    记录一次增长实验结果到知识库
    """
    try:
        growth_memory.record_cycle_result(
            segment=segment,
            strategy=strategy,
            ab_result={
                "significant": significant,
                "winning_variant": winning_variant,
                "lift_percent": lift_percent,
            },
            template_used="email_marketing",
        )
        return {"status": "recorded", "segment": segment, "strategy": strategy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
